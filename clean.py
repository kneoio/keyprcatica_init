from database.cleaner import clean_tables
from util.logging import logger

if __name__ == "__main__":
    logger.info("Starting the cleanup process...")
    clean_tables()
    logger.info("Cleanup process finished.")
