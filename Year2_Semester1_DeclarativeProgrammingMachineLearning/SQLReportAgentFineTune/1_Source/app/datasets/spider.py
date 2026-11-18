"""Spider Benchmark (Yale) downloader, schema parser, and dataset loader."""

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import requests
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import SchemaManager

logger = get_logger(__name__)

SPIDER_URL = "https://drive.google.com/uc?export=download&id=1_AckYkinAnHQmRmrHNIUC5S526KnvC--&confirm=t"
HF_SPIDER_URL = "https://huggingface.co/datasets/spider/raw/main/"


@dataclass
class SpiderItem:
    db_id: str
    question: str
    query: str


class SpiderDataset:
    """Manages acquisition and formatting of the Yale Spider Text-to-SQL Benchmark."""

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None):
        if raw_dir is None:
            self.raw_dir = get_project_root() / "2_Database" / "raw" / "spider"
        else:
            self.raw_dir = Path(raw_dir).resolve()
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def get_bundled_spider_examples(self) -> List[SpiderItem]:
        """Returns certified baseline Spider examples with clean SQLite schemas."""
        return [
            SpiderItem(
                db_id="concert_singer",
                question="How many singers do we have?",
                query="SELECT COUNT(*) FROM singer",
            ),
            SpiderItem(
                db_id="concert_singer",
                question="What is the average, minimum, and maximum age of all singers from France?",
                query="SELECT AVG(age), MIN(age), MAX(age) FROM singer WHERE country = 'France'",
            ),
            SpiderItem(
                db_id="concert_singer",
                question="Show singer name and the song name of all songs released after 2010.",
                query="SELECT singer.name, song.song_name FROM singer JOIN song ON singer.singer_id = song.singer_id WHERE song.release_year > 2010",
            ),
            SpiderItem(
                db_id="flight_2",
                question="Find the total number of airports located in California.",
                query="SELECT COUNT(*) FROM airports WHERE state = 'CA'",
            ),
            SpiderItem(
                db_id="flight_2",
                question="Which airline has the highest number of flights departing from San Francisco?",
                query="SELECT airlines.airline_name, COUNT(flights.flight_id) AS flight_count FROM airlines JOIN flights ON airlines.airline_id = flights.airline_id JOIN airports ON flights.source_airport = airports.airport_code WHERE airports.city = 'San Francisco' GROUP BY airlines.airline_id ORDER BY flight_count DESC LIMIT 1",
            ),
            SpiderItem(
                db_id="world_1",
                question="What are the official languages spoken in Switzerland?",
                query="SELECT language FROM countrylanguage JOIN country ON countrylanguage.countrycode = country.code WHERE country.name = 'Switzerland' AND countrylanguage.isofficial = 'T'",
            ),
            SpiderItem(
                db_id="world_1",
                question="List the top 5 most populous cities along with their country names.",
                query="SELECT city.name, country.name, city.population FROM city JOIN country ON city.countrycode = country.code ORDER BY city.population DESC LIMIT 5",
            ),
        ]

    def setup_bundled_databases(self) -> Dict[str, Path]:
        """Creates SQLite databases for bundled spider samples."""
        db_dir = self.raw_dir / "database"
        db_dir.mkdir(parents=True, exist_ok=True)

        # 1. concert_singer
        cs_path = db_dir / "concert_singer.db"
        cs_ddl = """
        CREATE TABLE singer (
            singer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            age INTEGER NOT NULL
        );
        CREATE TABLE song (
            song_id INTEGER PRIMARY KEY,
            singer_id INTEGER NOT NULL,
            song_name TEXT NOT NULL,
            release_year INTEGER NOT NULL,
            FOREIGN KEY (singer_id) REFERENCES singer(singer_id)
        );
        """
        cs_data = """
        INSERT INTO singer VALUES (1, 'Ed Sheeran', 'United Kingdom', 33), (2, 'Daft Punk', 'France', 48), (3, 'Stromae', 'Belgium', 39), (4, 'Zaz', 'France', 44);
        INSERT INTO song VALUES (1, 1, 'Shape of You', 2017), (2, 2, 'Get Lucky', 2013), (3, 3, 'Papaoutai', 2013), (4, 4, 'Je Veux', 2010);
        """
        SchemaManager.create_database_from_ddl(cs_path, cs_ddl, cs_data)

        # 2. flight_2
        fl_path = db_dir / "flight_2.db"
        fl_ddl = """
        CREATE TABLE airports (
            airport_code TEXT PRIMARY KEY,
            airport_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL
        );
        CREATE TABLE airlines (
            airline_id INTEGER PRIMARY KEY,
            airline_name TEXT NOT NULL,
            country TEXT NOT NULL
        );
        CREATE TABLE flights (
            flight_id INTEGER PRIMARY KEY,
            airline_id INTEGER NOT NULL,
            flight_number TEXT NOT NULL,
            source_airport TEXT NOT NULL,
            dest_airport TEXT NOT NULL,
            FOREIGN KEY (airline_id) REFERENCES airlines(airline_id),
            FOREIGN KEY (source_airport) REFERENCES airports(airport_code),
            FOREIGN KEY (dest_airport) REFERENCES airports(airport_code)
        );
        """
        fl_data = """
        INSERT INTO airports VALUES ('SFO', 'San Francisco Intl', 'San Francisco', 'CA'), ('LAX', 'Los Angeles Intl', 'Los Angeles', 'CA'), ('JFK', 'John F Kennedy Intl', 'New York', 'NY');
        INSERT INTO airlines VALUES (1, 'Delta Air Lines', 'USA'), (2, 'United Airlines', 'USA'), (3, 'SkyWest', 'USA');
        INSERT INTO flights VALUES (101, 2, 'UA100', 'SFO', 'JFK'), (102, 2, 'UA101', 'SFO', 'LAX'), (103, 1, 'DL200', 'LAX', 'JFK'), (104, 3, 'OO300', 'SFO', 'LAX');
        """
        SchemaManager.create_database_from_ddl(fl_path, fl_ddl, fl_data)

        # 3. world_1
        w_path = db_dir / "world_1.db"
        w_ddl = """
        CREATE TABLE country (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            continent TEXT NOT NULL,
            population INTEGER NOT NULL
        );
        CREATE TABLE city (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            countrycode TEXT NOT NULL,
            population INTEGER NOT NULL,
            FOREIGN KEY (countrycode) REFERENCES country(code)
        );
        CREATE TABLE countrylanguage (
            countrycode TEXT NOT NULL,
            language TEXT NOT NULL,
            isofficial TEXT NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (countrycode, language),
            FOREIGN KEY (countrycode) REFERENCES country(code)
        );
        """
        w_data = """
        INSERT INTO country VALUES ('CHE', 'Switzerland', 'Europe', 8600000), ('JPN', 'Japan', 'Asia', 125000000), ('USA', 'United States', 'North America', 331000000);
        INSERT INTO city VALUES (1, 'Tokyo', 'JPN', 37400000), (2, 'New York', 'USA', 8300000), (3, 'Zurich', 'CHE', 430000), (4, 'Geneva', 'CHE', 200000);
        INSERT INTO countrylanguage VALUES ('CHE', 'German', 'T', 63.5), ('CHE', 'French', 'T', 22.5), ('CHE', 'Italian', 'T', 8.1), ('JPN', 'Japanese', 'T', 99.0);
        """
        SchemaManager.create_database_from_ddl(w_path, w_ddl, w_data)

        return {
            "concert_singer": cs_path,
            "flight_2": fl_path,
            "world_1": w_path,
        }
