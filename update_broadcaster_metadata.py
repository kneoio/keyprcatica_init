# batch_metadata_updater.py

import os
import boto3
import tempfile
from dotenv import load_dotenv

from util.audio_metadata_parser import AudioMetadataParser
from util.logging import logger
from database import get_connection


class ExistingMetadataUpdater:
    def __init__(self):
        load_dotenv()

        self.access_key = os.getenv('DO_SPACES_KEY')
        self.secret_key = os.getenv('DO_SPACES_SECRET')
        self.region = os.getenv('DO_SPACES_REGION')
        self.endpoint = os.getenv('DO_SPACES_ENDPOINT')
        self.bucket_name = os.getenv('DO_SPACES_BUCKET')

        if not all([self.access_key, self.secret_key, self.region, self.endpoint, self.bucket_name]):
            logger.error("DigitalOcean Spaces configuration is missing.")
            raise ValueError("Missing DO Spaces configuration")

        self.s3_client = None
        self.metadata_parser = AudioMetadataParser(logger)
        self._init_s3_client()

    def _init_s3_client(self):
        try:
            s3_session = boto3.session.Session()
            self.s3_client = s3_session.client(
                's3',
                region_name=self.region,
                endpoint_url=f"https://{self.endpoint}",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            logger.info("S3 client initialized.")
        except Exception as e:
            logger.critical(f"Failed to initialize S3 client: {e}")
            raise

    def run_update(self, record_ids=None, limit=None, batch_size=50):
        conn = None
        updated_count = 0
        processed_count = 0
        total_fetched_for_processing = 0

        try:
            conn = get_connection()
            logger.info("Database connection established.")

            while True:
                cursor = conn.cursor()

                current_batch_limit = batch_size
                if limit is not None:
                    remaining_limit = limit - total_fetched_for_processing
                    if remaining_limit <= 0: break
                    current_batch_limit = min(batch_size, remaining_limit)

                query_params = []
                base_query = """
                    SELECT id, do_key, artist, title, album 
                    FROM kneobroadcaster__sound_fragments
                    WHERE do_key IS NOT NULL
                """

                if record_ids:
                    base_query += " AND id = ANY(%s)"
                    query_params.append(list(record_ids))
                    current_batch_limit = len(record_ids)

                base_query += " ORDER BY id ASC"

                if current_batch_limit > 0 and not record_ids:
                    base_query += " OFFSET %s LIMIT %s"
                    query_params.extend([total_fetched_for_processing, current_batch_limit])
                elif record_ids and current_batch_limit > 0:
                    base_query += " LIMIT %s"
                    query_params.append(current_batch_limit)

                logger.info(
                    f"Fetching batch. Offset: {total_fetched_for_processing if not record_ids else 0}, Limit: {current_batch_limit}")
                cursor.execute(base_query, tuple(query_params))
                records_to_process = cursor.fetchall()
                cursor.close()

                if not records_to_process:
                    logger.info("No more records found to process.")
                    break

                batch_processed_this_iteration = len(records_to_process)
                total_fetched_for_processing += batch_processed_this_iteration
                logger.info(f"Fetched {batch_processed_this_iteration} records.")

                for db_id, do_key, current_artist, current_title, current_album in records_to_process:
                    processed_count += 1
                    logger.info(f"Processing ID: {db_id}, Key: {do_key}")

                    if not do_key:
                        logger.warning(f"Skipping ID: {db_id}, missing DO Key.")
                        continue

                    temp_audio_file_path = None

                    try:
                        file_suffix = os.path.splitext(do_key)[1] if do_key else ".tmp"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_f:
                            self.s3_client.download_fileobj(self.bucket_name, do_key, tmp_f)
                            temp_audio_file_path = tmp_f.name

                        if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                            parsed_meta = self.metadata_parser.parse_metadata(temp_audio_file_path)
                        else:
                            logger.warning(f"Temp file not available for ID: {db_id}.")

                    except Exception as e_download_parse:
                        logger.error(f"Error downloading/parsing for Key '{do_key}' (ID: {db_id}): {e_download_parse}")
                        continue
                    finally:
                        if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                            try:
                                os.remove(temp_audio_file_path)
                            except OSError as e_remove:
                                logger.warning(f"Could not remove temp file '{temp_audio_file_path}': {e_remove}")

                    if not parsed_meta:
                        logger.warning(f"Metadata parsing returned no data for ID: {db_id}.")
                        meta_artist, meta_title, meta_album = None, None, None
                    else:
                        meta_artist = parsed_meta.get("artist")
                        meta_title = parsed_meta.get("title")
                        meta_album = parsed_meta.get("album")

                    update_payload = {}

                    new_artist_val = meta_artist if meta_artist is not None else ''
                    if new_artist_val != (current_artist or ''):
                        update_payload['artist'] = new_artist_val

                    new_title_val = meta_title if meta_title is not None else ''
                    if new_title_val != (current_title or ''):
                        update_payload['title'] = new_title_val

                    new_album_val = meta_album if meta_album is not None else ''
                    if new_album_val != (current_album or ''):
                        update_payload['album'] = new_album_val

                    if update_payload:
                        update_query_parts = []
                        update_values = []
                        for col, val in update_payload.items():
                            update_query_parts.append(f"{col} = %s")
                            update_values.append(val)

                        update_values.append(db_id)
                        sql_update = f"UPDATE kneobroadcaster__sound_fragments SET {', '.join(update_query_parts)} WHERE id = %s"

                        update_cursor = None
                        try:
                            update_cursor = conn.cursor()
                            logger.info(f"  Updating ID {db_id}: SET {update_payload}")
                            update_cursor.execute(sql_update, tuple(update_values))
                            conn.commit()
                            updated_count += 1
                            logger.info(f"  Successfully updated ID: {db_id}")
                        except Exception as e_update:
                            logger.error(f"  Failed to update ID: {db_id}. Error: {e_update}")
                            conn.rollback()
                        finally:
                            if update_cursor: update_cursor.close()
                    else:
                        logger.info(f"No changes needed for ID: {db_id}.")

                if record_ids: break
                if limit is not None and total_fetched_for_processing >= limit: break
                if batch_processed_this_iteration < current_batch_limit and current_batch_limit == batch_size: break

            logger.info(
                f"\nUpdate finished. Total records considered: {total_fetched_for_processing}. Processed: {processed_count}. Updated: {updated_count}.")

        except Exception as e:
            logger.error(f"Critical error during update process: {e}", exc_info=True)
            if conn: conn.rollback()
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed.")


if __name__ == "__main__":
    record_ids_to_process = None
    limit_run = None

    updater = ExistingMetadataUpdater()
    try:
        updater.run_update(
            record_ids=record_ids_to_process,
            limit=limit_run
        )
    except Exception as e_main_run:
        logger.critical(f"Updater run failed: {e_main_run}", exc_info=True)
    finally:
        logger.info("Existing metadata update process has concluded.")
