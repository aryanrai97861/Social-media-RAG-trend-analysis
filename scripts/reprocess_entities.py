#!/usr/bin/env python3
"""
Reprocess existing posts to recompute entities using the updated feature extractor
"""
import logging
import sys
import os
from sqlalchemy import text as sql_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import get_engine
from pipeline.features import extract_entities


def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main(batch_size: int = 500):
    setup_logging()
    engine = get_engine()

    logging.info("Starting reprocess of post entities")
    with engine.connect() as conn:
        result = conn.execute(sql_text("SELECT id, text FROM posts"))
        rows = result.fetchall()

    total = len(rows)
    logging.info(f"Found {total} posts to reprocess")

    updated = 0
    # Process in batches
    for i in range(0, total, batch_size):
        batch = rows[i:i+batch_size]
        updates = []
        for row in batch:
            # SQLAlchemy Row may not support dict-like access depending on driver; use index access
            post_id = row[0]
            post_text = row[1]
            try:
                entities = extract_entities(post_text)
                entities_str = ','.join(entities)
                updates.append({'id': post_id, 'entities': entities_str})
            except Exception as e:
                logging.warning(f"Failed to extract entities for post {post_id}: {e}")

        # Apply updates in a transaction
        if updates:
            with engine.begin() as conn:
                for u in updates:
                    conn.execute(sql_text("UPDATE posts SET entities = :entities WHERE id = :id"), u)
            updated += len(updates)
            logging.info(f"Updated {updated}/{total} posts")

    logging.info(f"Reprocessing complete. Total updated: {updated}")


if __name__ == '__main__':
    main()
