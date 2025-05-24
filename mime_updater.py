import os
import boto3
import magic
from dotenv import load_dotenv

from util.mime_utils import determine_mime_type
from database import get_connection
from util.logging import logger

MIME_DETECTION_READ_BYTES = 2048


class MimeTypeUpdater:
    def __init__(self):
        load_dotenv()
        self.access_key = os.getenv('DO_SPACES_KEY')
        self.secret_key = os.getenv('DO_SPACES_SECRET')
        self.region = os.getenv('DO_SPACES_REGION')
        self.endpoint = os.getenv('DO_SPACES_ENDPOINT')
        self.bucket_name = os.getenv('DO_SPACES_BUCKET')

        if not all([self.access_key, self.secret_key, self.region, self.endpoint, self.bucket_name]):
            logger.error("S3 configuration missing. Please check .env file.")
            raise ValueError("S3 configuration missing.")

        try:
            session = boto3.session.Session()
            self.s3_client = session.client(
                's3',
                region_name=self.region,
                endpoint_url=f"https://{self.endpoint}",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            self.mime_detector = magic.Magic(mime=True)
        except Exception as e:
            logger.error(f"Failed to initialize S3 client or magic: {e}")
            raise

        self.logger = logger

    def update_mime_types_in_db(self):
        conn = None
        cursor = None
        updated_count = 0
        checked_count = 0

        try:
            conn = get_connection()
            if conn is None:
                self.logger.error("Failed to get database connection.")
                return

            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, do_key, mime_type 
                FROM kneobroadcaster__sound_fragments 
                WHERE mime_type = %s OR mime_type IS NULL
            """, ("application/octet-stream",))

            records_to_update = cursor.fetchall()

            if not records_to_update:
                self.logger.info(
                    "No sound fragments found with undetermined MIME types ('application/octet-stream' or NULL).")
                return

            self.logger.info(f"Found {len(records_to_update)} records to check for MIME type updates.")

            for record in records_to_update:
                record_id, file_key, current_mime_type = record
                checked_count += 1

                if not file_key:
                    self.logger.warning(f"Record ID {record_id} has no 'do_key'. Skipping.")
                    continue

                filename = os.path.basename(file_key)

                self.logger.debug(
                    f"Processing record ID {record_id}, file_key: {file_key}, current_mime: {current_mime_type}")

                new_mime_type = determine_mime_type(
                    s3_client=self.s3_client,
                    bucket_name=self.bucket_name,
                    file_key=file_key,
                    filename=filename,
                    mime_detector=self.mime_detector,
                    logger=self.logger,
                    read_bytes=MIME_DETECTION_READ_BYTES
                )

                if new_mime_type != "application/octet-stream" and new_mime_type != current_mime_type:
                    try:
                        cursor.execute("""
                            UPDATE kneobroadcaster__sound_fragments
                            SET mime_type = %s
                            WHERE id = %s
                        """, (new_mime_type, record_id))
                        conn.commit()
                        updated_count += 1
                        self.logger.info(
                            f"Updated MIME type for record ID {record_id} (Key: {file_key}) from '{current_mime_type}' to '{new_mime_type}'.")
                    except Exception as e_update:
                        conn.rollback()
                        self.logger.error(f"Failed to update MIME type for record ID {record_id}: {e_update}")
                elif new_mime_type == current_mime_type:
                    self.logger.debug(
                        f"MIME type for record ID {record_id} (Key: {file_key}) is already correctly set to '{current_mime_type}'. No update needed.")
                else:
                    self.logger.debug(
                        f"Could not determine a better MIME type for {file_key} (still '{new_mime_type}'). Original was '{current_mime_type}'. No update performed.")

            self.logger.info(
                f"MIME type update process finished. Checked {checked_count} records. Updated {updated_count} records.")

        except Exception as e:
            self.logger.error(f"An error occurred during the MIME type update process: {e}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


if __name__ == "__main__":
    logger.info("Starting MIME Type Updater process...")
    updater = MimeTypeUpdater()
    updater.update_mime_types_in_db()
    logger.info("MIME Type Updater process finished.")