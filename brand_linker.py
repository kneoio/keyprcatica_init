import json
import os
from datetime import datetime
from dotenv import load_dotenv
from database import get_connection  # Assuming database.py and get_connection exist
from util.logging import logger  # Assuming util/logging.py and logger exist

load_dotenv()

TARGET_BRAND_SLUG = "nitroglycerin"
MAX_SONGS_PER_BRAND = 50
DRY_RUN = False  # Set to True to see what would be unlinked and linked without actual changes
GENRE_TO_UNLINK = "electronic"  # Genre to specifically unlink


class BrandSoundFragmentLinker:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.target_brand_id = None
        self.target_brand_slug = None

    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_brand_info(self, brand_slug):
        try:
            self.cursor.execute(
                "SELECT id, slug_name FROM kneobroadcaster__brands WHERE slug_name = %s",
                (brand_slug,)
            )
            result = self.cursor.fetchone()

            if result:
                brand_id, slug_name = result
                logger.info(f"Found brand: ID={brand_id}, Slug='{slug_name}'")
                return brand_id, slug_name, None
            else:
                logger.error(f"Brand with slug '{brand_slug}' not found in database")
                return None, None, None
        except Exception as e:
            logger.error(f"Error fetching brand info: {e}")
            return None, None, None

    def unlink_fragments_by_genre(self, brand_id, genre_to_unlink):
        logger.info(f"Attempting to unlink fragments of genre '{genre_to_unlink}' for brand ID {brand_id}")
        genre_to_unlink_lower = genre_to_unlink.lower()
        unlinked_count = 0

        try:
            if DRY_RUN:
                self.cursor.execute("""
                    SELECT sf.id, sf.title, sf.artist
                    FROM kneobroadcaster__brand_sound_fragments bsf
                    JOIN kneobroadcaster__sound_fragments sf ON bsf.sound_fragment_id = sf.id
                    WHERE bsf.brand_id = %s AND LOWER(sf.genre) = %s
                """, (brand_id, genre_to_unlink_lower))
                fragments_to_unlink_info = self.cursor.fetchall()
                unlinked_count = len(fragments_to_unlink_info)
                if unlinked_count > 0:
                    logger.info(f"[DRY RUN] Would unlink {unlinked_count} fragments of genre '{genre_to_unlink}':")
                    for fid, title, artist in fragments_to_unlink_info[:10]:  # Log sample
                        logger.info(f"  - [DRY RUN] Would unlink ID: {fid}, Title: '{title}', Artist: '{artist}'")
                    if unlinked_count > 10:
                        logger.info(f"  ... and {unlinked_count - 10} more.")
                else:
                    logger.info(f"[DRY RUN] No fragments of genre '{genre_to_unlink}' found linked to this brand.")
            else:
                # Subquery method for broader compatibility
                delete_query = """
                    DELETE FROM kneobroadcaster__brand_sound_fragments
                    WHERE brand_id = %s
                      AND sound_fragment_id IN (
                          SELECT id
                          FROM kneobroadcaster__sound_fragments
                          WHERE LOWER(genre) = %s
                      );
                """
                self.cursor.execute(delete_query, (brand_id, genre_to_unlink_lower))
                unlinked_count = self.cursor.rowcount
                self.conn.commit()
                if unlinked_count > 0:
                    logger.info(f"Successfully unlinked {unlinked_count} fragments of genre '{genre_to_unlink}'.")
                else:
                    logger.info(f"No fragments of genre '{genre_to_unlink}' were found linked to this brand to unlink.")
            return unlinked_count
        except Exception as e:
            logger.error(f"Error unlinking fragments by genre '{genre_to_unlink}': {e}")
            if not DRY_RUN:
                self.conn.rollback()
            return 0

    def get_existing_brand_fragments(self, brand_id):
        try:
            self.cursor.execute("""
                SELECT sf.id, sf.title, sf.artist, bsf.played_by_brand_count, bsf.last_time_played_by_brand
                FROM kneobroadcaster__brand_sound_fragments bsf
                JOIN kneobroadcaster__sound_fragments sf ON bsf.sound_fragment_id = sf.id
                WHERE bsf.brand_id = %s AND sf.archived = 0
                ORDER BY sf.title, sf.artist
            """, (brand_id,))
            existing_fragments = self.cursor.fetchall()
            logger.info(f"Brand currently has {len(existing_fragments)} linked sound fragments (after any unlinking).")
            if existing_fragments:
                logger.info("Sample of current linked fragments:")
                for i, (fragment_id, title, artist, play_count, last_played) in enumerate(existing_fragments[:5]):
                    logger.info(f"  - ID:{fragment_id} '{title}' by '{artist}' (plays: {play_count})")
                if len(existing_fragments) > 5:
                    logger.info(f"  ... and {len(existing_fragments) - 5} more")
            return {row[0] for row in existing_fragments}
        except Exception as e:
            logger.error(f"Error fetching existing brand fragments: {e}")
            return set()

    def get_unlinked_fragments(self, brand_id, limit=None):
        try:
            query = """
                SELECT sf.id, sf.title, sf.artist, sf.album, sf.genre, sf.reg_date
                FROM kneobroadcaster__sound_fragments sf
                WHERE sf.archived = 0 
                AND sf.status = 1
                AND LOWER(sf.genre) != %s 
                AND sf.id NOT IN (
                    SELECT bsf.sound_fragment_id 
                    FROM kneobroadcaster__brand_sound_fragments bsf 
                    WHERE bsf.brand_id = %s
                )
                ORDER BY sf.reg_date DESC, sf.title, sf.artist
            """
            if limit:
                query += f" LIMIT {limit}"
            self.cursor.execute(query, (GENRE_TO_UNLINK.lower(), brand_id,))  # Exclude the same genre we unlinked
            unlinked_fragments = self.cursor.fetchall()
            logger.info(
                f"Found {len(unlinked_fragments)} unlinked fragments (excluding '{GENRE_TO_UNLINK}' genre) available for new linking.")
            return unlinked_fragments
        except Exception as e:
            logger.error(f"Error fetching unlinked fragments (excluding '{GENRE_TO_UNLINK}'): {e}")
            return []

    def link_fragments_to_brand(self, brand_id, fragments_to_link):
        if not fragments_to_link:
            logger.info("No new fragments to link.")
            return 0
        linked_count = 0
        try:
            for fragment_id, title, artist, album, genre, reg_date in fragments_to_link:
                try:
                    if DRY_RUN:
                        logger.info(f"[DRY RUN] Would link: ID:{fragment_id} '{title}' by '{artist}' (Genre: {genre})")
                        linked_count += 1
                        continue
                    self.cursor.execute("""
                        INSERT INTO kneobroadcaster__brand_sound_fragments 
                        (brand_id, sound_fragment_id, played_by_brand_count, last_time_played_by_brand)
                        VALUES (%s, %s, %s, %s)
                    """, (brand_id, fragment_id, 0, None))
                    linked_count += 1
                    logger.info(f"Linked fragment ID:{fragment_id} '{title}' by '{artist}' (Genre: {genre}) to brand.")
                except Exception as e_fragment:
                    logger.error(f"Error linking fragment ID:{fragment_id} '{title}': {e_fragment}")
                    continue
            if not DRY_RUN:
                self.conn.commit()
                logger.info(f"Successfully committed {linked_count} new brand-sound fragment links.")
            else:
                logger.info(f"[DRY RUN] Would have linked {linked_count} new fragments.")
            return linked_count
        except Exception as e:
            logger.error(f"Error during bulk linking: {e}")
            if not DRY_RUN:
                self.conn.rollback()
            return linked_count

    def show_brand_fragment_stats(self, brand_id):
        # This method remains the same, shows current state
        try:
            self.cursor.execute("SELECT COUNT(*) FROM kneobroadcaster__brand_sound_fragments WHERE brand_id = %s",
                                (brand_id,))
            total_count = self.cursor.fetchone()[0]
            self.cursor.execute("""
                SELECT sf.genre, COUNT(*) as fragment_count
                FROM kneobroadcaster__brand_sound_fragments bsf
                JOIN kneobroadcaster__sound_fragments sf ON bsf.sound_fragment_id = sf.id
                WHERE bsf.brand_id = %s AND sf.archived = 0
                GROUP BY sf.genre ORDER BY fragment_count DESC
            """, (brand_id,))
            genre_stats = self.cursor.fetchall()
            logger.info(f"\n=== Brand Fragment Statistics (Post-Operation) ===")
            logger.info(f"Total fragments currently linked to brand: {total_count}")
            if genre_stats:
                logger.info(f"\nBy Genre:")
                for genre, count in genre_stats:
                    logger.info(f"  {(genre if genre else 'Unknown')}: {count} fragments")
        except Exception as e:
            logger.error(f"Error generating brand fragment stats: {e}")

    def run_linking_process(self, brand_slug, max_songs=MAX_SONGS_PER_BRAND):
        logger.info(f"Starting brand sound fragment processing for: {brand_slug}")
        logger.info(f"Max songs per brand: {max_songs}")
        logger.info(f"Dry run mode: {DRY_RUN}")
        logger.info(f"Genre to automatically UNLINK if found: '{GENRE_TO_UNLINK}'")
        logger.info(f"Genre to AVOID linking if new: '{GENRE_TO_UNLINK}'")

        brand_id, brand_slug_name, _ = self.get_brand_info(brand_slug)
        if not brand_id:
            logger.error("Cannot proceed without valid brand information.")
            return False

        self.target_brand_id = brand_id
        self.target_brand_slug = brand_slug_name

        # Step 1: Unlink fragments of the specified genre
        self.unlink_fragments_by_genre(brand_id, GENRE_TO_UNLINK)

        # Step 2: Get current state after unlinking
        existing_fragment_ids = self.get_existing_brand_fragments(brand_id)
        current_count = len(existing_fragment_ids)

        songs_to_add = max(0, max_songs - current_count)

        if songs_to_add == 0:
            logger.info(
                f"Brand '{brand_slug}' currently has {current_count} fragments (max: {max_songs}). No new fragments need to be linked, or no space available.")
            self.show_brand_fragment_stats(brand_id)
            return True  # Considered success as the state is as desired or no action needed for linking.

        logger.info(
            f"Brand currently has {current_count} fragments. Can add {songs_to_add} more (excluding '{GENRE_TO_UNLINK}' genre).")

        # Step 3: Get unlinked fragments (excluding the specified genre)
        unlinked_fragments_to_consider = self.get_unlinked_fragments(brand_id, limit=songs_to_add)

        if not unlinked_fragments_to_consider:
            logger.info(
                f"No suitable unlinked fragments (excluding '{GENRE_TO_UNLINK}' genre) available for this brand.")
            self.show_brand_fragment_stats(brand_id)
            return True  # No action to take for linking.

        fragments_to_link = unlinked_fragments_to_consider[:songs_to_add]

        logger.info(
            f"Will attempt to link {len(fragments_to_link)} new non-'{GENRE_TO_UNLINK}' fragments to brand '{brand_slug}'")

        if fragments_to_link:
            logger.info("Sample of new fragments to be linked:")
            for i, (frag_id, title, artist, album, genre, _) in enumerate(fragments_to_link[:5]):
                logger.info(f"  - ID:{frag_id} '{title}' by '{artist}' (Genre: {genre})")
            if len(fragments_to_link) > 5:
                logger.info(f"  ... and {len(fragments_to_link) - 5} more")

        # Step 4: Perform the linking
        linked_count = self.link_fragments_to_brand(brand_id, fragments_to_link)

        if linked_count > 0:
            logger.info(
                f"Successfully linked {linked_count} new non-'{GENRE_TO_UNLINK}' fragments to brand '{brand_slug}'.")
        elif not fragments_to_link:
            logger.info(f"No non-'{GENRE_TO_UNLINK}' fragments were available to attempt linking in this run.")
        else:  # fragments_to_link was not empty, but linked_count is 0
            logger.warning(
                f"Attempted to link {len(fragments_to_link)} fragments, but none were successfully linked in this run (check for individual errors).")

        self.show_brand_fragment_stats(brand_id)
        return True  # Process completed, success status depends on whether operations were intended.


def main():
    logger.info("=" * 60)
    logger.info("BRAND SOUND FRAGMENT LINKER & CLEANER")
    logger.info("=" * 60)

    try:
        with BrandSoundFragmentLinker() as linker:
            linker.run_linking_process(TARGET_BRAND_SLUG, MAX_SONGS_PER_BRAND)
        logger.info("Brand sound fragment processing completed.")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
    except Exception as e:
        logger.error(f"Critical error during brand linking process: {e}", exc_info=True)
    finally:
        logger.info("Brand sound fragment linker & cleaner finished.")


if __name__ == "__main__":
    main()