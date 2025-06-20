#!/usr/bin/env python3
"""
CRUCH - Enhanced Leet Speak Wordlist Generator
A wrapper and subroutine handler for advanced leetspeak wordlist generation
with crunch-like functionality and improved error handling.
m4tth4ck
Original leet.py by Tim Tomes (LaNMaSteR53)
Enhanced wrapper by: Enhanced Development Team
"""

import sys
import os
import csv
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import itertools
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cruch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Leetspeak dictionary
LEET_DICT = {
    'a': ['4', '@'],
    'e': ['3'],
    'g': ['6'],
    'i': ['1', '!'],
    'l': ['7', '1', '!'],
    'n': ['^'],
    'o': ['0'],
    'q': ['0'],
    's': ['5', '$'],
    't': ['7'],
    'v': ['\/'],
}

# Database setup
Base = declarative_base()


class WordVariant(Base):
    __tablename__ = 'variants'
    id = Column(Integer, primary_key=True)
    base = Column(String)
    variant = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class CruchError(Exception):
    """Custom exception for Cruch operations"""
    pass


class SubroutineHandler:
    """Handles all subroutines for wordlist generation and manipulation"""

    def __init__(self):
        self.engine = None
        self.session = None
        self.wordlist_cache: Set[str] = set()

    def init_database(self, db_path: str = 'cruch_wordlists.db') -> None:
        """Initialize database connection"""
        try:
            self.engine = create_engine(f'sqlite:///{db_path}')
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            logger.info(f"Database initialized: {db_path}")
        except Exception as e:
            raise CruchError(f"Database initialization failed: {e}")

    def load_wordlist(self, source: str) -> List[str]:
        """Load wordlist from file or stdin"""
        try:
            if source == '-':
                wordlist = sys.stdin.read().strip().split('\n')
                logger.info("Loaded wordlist from stdin")
            else:
                path = Path(source)
                if not path.exists():
                    raise CruchError(f"File not found: {source}")

                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    wordlist = [line.strip() for line in f if line.strip()]
                logger.info(f"Loaded {len(wordlist)} words from {source}")

            return [word for word in wordlist if word]
        except Exception as e:
            raise CruchError(f"Failed to load wordlist: {e}")

    def generate_leet_variants(self, wordlist: List[str], max_variants: int = 1000) -> List[str]:
        """Generate leetspeak variants with limit protection"""
        variants = set(wordlist)  # Start with original words

        try:
            for word in wordlist:
                if len(variants) >= max_variants:
                    logger.warning(f"Reached max variants limit: {max_variants}")
                    break

                word_variants = self._generate_word_variants(word)
                variants.update(word_variants)

                # Progress logging for large wordlists
                if len(wordlist) > 100 and wordlist.index(word) % 50 == 0:
                    logger.info(f"Processed {wordlist.index(word)}/{len(wordlist)} words")

            logger.info(f"Generated {len(variants)} total variants")
            return list(variants)
        except Exception as e:
            raise CruchError(f"Leet variant generation failed: {e}")

    def _generate_word_variants(self, word: str) -> Set[str]:
        """Generate all possible leet variants for a single word"""
        variants = set()

        # Generate character-by-character substitutions
        for i, char in enumerate(word):
            if char.lower() in LEET_DICT:
                for replacement in LEET_DICT[char.lower()]:
                    variant = word[:i] + replacement + word[i + 1:]
                    variants.add(variant)

        return variants

    def apply_case_mutations(self, wordlist: List[str]) -> List[str]:
        """Apply case mutations to wordlist"""
        try:
            mutated = set(wordlist)

            for word in wordlist:
                # Add common case variations
                mutated.add(word.upper())
                mutated.add(word.lower())
                mutated.add(word.capitalize())
                mutated.add(word.title())

                # Add character-by-character case swapping
                for i in range(len(word)):
                    chars = list(word)
                    chars[i] = chars[i].swapcase()
                    mutated.add(''.join(chars))

            logger.info(f"Applied case mutations: {len(mutated)} total variants")
            return list(mutated)
        except Exception as e:
            raise CruchError(f"Case mutation failed: {e}")

    def generate_crunch_patterns(self, min_len: int, max_len: int, charset: str = None) -> List[str]:
        """Generate crunch-like patterns"""
        if not charset:
            charset = string.ascii_lowercase + string.digits

        patterns = []

        try:
            for length in range(min_len, max_len + 1):
                if length > 4:  # Prevent memory issues
                    logger.warning(f"Skipping length {length} to prevent memory issues")
                    continue

                for pattern in itertools.product(charset, repeat=length):
                    patterns.append(''.join(pattern))

                    if len(patterns) >= 10000:  # Limit to prevent memory issues
                        logger.warning("Reached pattern generation limit")
                        return patterns

            logger.info(f"Generated {len(patterns)} crunch patterns")
            return patterns
        except Exception as e:
            raise CruchError(f"Crunch pattern generation failed: {e}")

    def save_wordlist(self, wordlist: List[str], output_format: str, output_file: str = None,
                      base_word: str = "unknown") -> None:
        """Save wordlist in specified format"""
        try:
            if output_format.lower() == 'json':
                self._save_json(wordlist, output_file, base_word)
            elif output_format.lower() == 'csv':
                self._save_csv(wordlist, output_file, base_word)
            elif output_format.lower() == 'db':
                self._save_database(wordlist, base_word)
            else:
                self._save_text(wordlist, output_file)

            logger.info(f"Wordlist saved in {output_format} format")
        except Exception as e:
            raise CruchError(f"Failed to save wordlist: {e}")

    def _save_json(self, wordlist: List[str], output_file: str, base_word: str) -> None:
        """Save as JSON format"""
        data = {
            "base_word": base_word,
            "generated_at": datetime.utcnow().isoformat(),
            "count": len(wordlist),
            "variants": sorted(set(wordlist))
        }

        output_file = output_file or f"{base_word}_variants.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_csv(self, wordlist: List[str], output_file: str, base_word: str) -> None:
        """Save as CSV format"""
        output_file = output_file or f"{base_word}_variants.csv"
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Base', 'Variant', 'Length', 'Generated_At'])
            timestamp = datetime.utcnow().isoformat()

            for word in sorted(set(wordlist)):
                writer.writerow([base_word, word, len(word), timestamp])

    def _save_database(self, wordlist: List[str], base_word: str) -> None:
        """Save to database"""
        if not self.session:
            self.init_database()

        for word in set(wordlist):
            entry = WordVariant(base=base_word, variant=word)
            self.session.add(entry)

        self.session.commit()

    def _save_text(self, wordlist: List[str], output_file: str) -> None:
        """Save as plain text"""
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                for word in sorted(set(wordlist)):
                    f.write(f"{word}\n")
        else:
            for word in sorted(set(wordlist)):
                print(word)


class CruchWrapper:
    """Main wrapper class for enhanced leet.py functionality"""

    def __init__(self):
        self.handler = SubroutineHandler()
        self.args = None

    def parse_arguments(self) -> argparse.Namespace:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description='CRUCH - Enhanced Leet Speak Wordlist Generator',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s -f wordlist.txt -c -l --output-format json
  %(prog)s -f - -c --max-variants 5000 --output output.txt
  %(prog)s --crunch 3 4 abc123 --output patterns.txt
  %(prog)s -f words.txt --recon-hooks --output-format db
            """
        )

        # Input options
        parser.add_argument('-f', '--file', help='Input wordlist file (- for stdin)')
        parser.add_argument('--crunch', nargs=3, metavar=('MIN', 'MAX', 'CHARSET'),
                            help='Generate crunch-like patterns (min_len max_len charset)')

        # Processing options
        parser.add_argument('-c', '--case', action='store_true',
                            help='Apply case mutations')
        parser.add_argument('-l', '--leet', action='store_true', default=True,
                            help='Apply leetspeak transformations (default: True)')
        parser.add_argument('--max-variants', type=int, default=10000,
                            help='Maximum number of variants to generate')

        # Output options
        parser.add_argument('--output-format', choices=['txt', 'json', 'csv', 'db'],
                            default='txt', help='Output format')
        parser.add_argument('--output', '-o', help='Output file path')

        # Tool integration
        parser.add_argument('--recon-hooks', action='store_true',
                            help='Generate recon tool integration commands')
        parser.add_argument('--jtr-rules', type=int, metavar='NUM',
                            help='Generate John the Ripper rules')

        # Utility options
        parser.add_argument('--view-dict', action='store_true',
                            help='View leetspeak dictionary')
        parser.add_argument('--db-path', default='cruch_wordlists.db',
                            help='Database file path')
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='Enable verbose logging')

        return parser.parse_args()

    def generate_jtr_rules(self, num_chars: int) -> None:
        """Generate John the Ripper rules"""
        print('[List.Rules:CruchWordlist]')
        for key in LEET_DICT.keys():
            for val in LEET_DICT[key]:
                for i in range(int(num_chars)):
                    print(f'={i}{key}o{i}{val}')

    def show_leet_dictionary(self) -> None:
        """Display the leetspeak dictionary"""
        print("Leetspeak Dictionary:")
        print("=" * 20)
        for key in sorted(LEET_DICT.keys()):
            print(f'{key} -> {", ".join(LEET_DICT[key])}')

    def generate_recon_hooks(self, base_word: str, output_file: str = None) -> None:
        """Generate reconnaissance tool integration commands"""
        print("\n" + "=" * 50)
        print("RECONNAISSANCE TOOL INTEGRATION")
        print("=" * 50)

        output_file = output_file or f"{base_word}_wordlist.txt"

        print(f"\n[Recon-ng Integration]:")
        print(f"recon-cli -w {base_word}_recon -m recon/domains-hosts/brute_hosts")
        print(f"  -x \"set WORDLIST {output_file}; run\"")

        print(f"\n[Gobuster Integration]:")
        print(f"gobuster dir -u http://target.com -w {output_file} -x php,html,txt")

        print(f"\n[FFuf Integration]:")
        print(f"ffuf -w {output_file}:FUZZ -u http://target.com/FUZZ")

        print(f"\n[Hydra Integration]:")
        print(f"hydra -L {output_file} -P {output_file} target.com ssh")

        print(f"\n[Hashcat Integration]:")
        print(f"hashcat -m 0 -a 0 hashes.txt {output_file}")

    def run(self) -> None:
        """Main execution method"""
        try:
            self.args = self.parse_arguments()

            if self.args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)

            # Handle utility functions
            if self.args.view_dict:
                self.show_leet_dictionary()
                return

            if self.args.jtr_rules:
                self.generate_jtr_rules(self.args.jtr_rules)
                return

            # Initialize database if needed
            if self.args.output_format == 'db':
                self.handler.init_database(self.args.db_path)

            # Load or generate wordlist
            wordlist = []
            base_word = "generated"

            if self.args.file:
                wordlist = self.handler.load_wordlist(self.args.file)
                base_word = Path(self.args.file).stem if self.args.file != '-' else "stdin"
            elif self.args.crunch:
                min_len, max_len, charset = self.args.crunch
                wordlist = self.handler.generate_crunch_patterns(
                    int(min_len), int(max_len), charset
                )
                base_word = f"crunch_{min_len}_{max_len}"
            else:
                raise CruchError("No input source specified. Use -f or --crunch")

            if not wordlist:
                raise CruchError("No words loaded or generated")

            # Apply transformations
            if self.args.leet:
                wordlist = self.handler.generate_leet_variants(
                    wordlist, self.args.max_variants
                )

            if self.args.case:
                wordlist = self.handler.apply_case_mutations(wordlist)

            # Save output
            self.handler.save_wordlist(
                wordlist, self.args.output_format, self.args.output, base_word
            )

            # Generate integration hooks if requested
            if self.args.recon_hooks:
                self.generate_recon_hooks(base_word, self.args.output)

            logger.info(f"Successfully processed {len(set(wordlist))} unique words")

        except CruchError as e:
            logger.error(f"Cruch Error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    wrapper = CruchWrapper()
    wrapper.run()


if __name__ == "__main__":
    main()