import os
import magic

DEFAULT_MIME_DETECTION_READ_BYTES = 2048


def determine_mime_type(s3_client, bucket_name, file_key, filename, mime_detector, logger,
                        read_bytes=DEFAULT_MIME_DETECTION_READ_BYTES):
    mime_type = "application/octet-stream"

    try:
        s3_object = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content_chunk = s3_object['Body'].read(read_bytes)
        if file_content_chunk:
            detected = mime_detector.from_buffer(file_content_chunk)
            if detected and detected != "application/octet-stream":
                mime_type = detected
            else:
                logger.debug(f"Magic returned '{detected}' for {file_key}. Checking extension.")
                if filename.lower().endswith(".mp3"):
                    mime_type = "audio/mpeg"
                elif filename.lower().endswith(".wav"):
                    mime_type = "audio/wav"
                elif detected:
                    mime_type = detected
        else:
            logger.warning(f"File {file_key} is empty or unreadable for MIME detection via content. Trying extension.")
            if filename.lower().endswith(".mp3"):
                mime_type = "audio/mpeg"
            elif filename.lower().endswith(".wav"):
                mime_type = "audio/wav"

    except Exception as e_magic:
        logger.error(f"MIME detection for {file_key} using magic failed: {e_magic}. Falling back to extension.")
        if filename.lower().endswith(".mp3"):
            mime_type = "audio/mpeg"
        elif filename.lower().endswith(".wav"):
            mime_type = "audio/wav"

    if mime_type == "application/octet-stream":
        logger.debug(f"MIME type for {file_key} is still 'application/octet-stream'. Attempting fallback by extension.")
        if filename.lower().endswith(".mp3"):
            mime_type = "audio/mpeg"
        elif filename.lower().endswith(".wav"):
            mime_type = "audio/wav"

    logger.debug(f"Determined MIME type for {file_key} ('{filename}'): {mime_type}")
    return mime_type