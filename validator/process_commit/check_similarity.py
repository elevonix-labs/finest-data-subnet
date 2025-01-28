# data_processing.py

import time
import random
import boto3
from warcio.archiveiterator import ArchiveIterator
from io import BytesIO
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datasets import load_dataset
import nltk
from nltk.corpus import stopwords
from collections import Counter
from utils import extract_commit

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    print("Downloading 'punkt' package...")
    nltk.download("punkt")

# try:
#     nltk.data.find('tokenizers/punkt_tab')
# except LookupError:
#     print("Downloading 'punkt_tab' package...")
#     nltk.download('punkt_tab')

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    print("Downloading 'stopwords' package...")
    nltk.download("stopwords")


class DataProcessor:
    def __init__(self, warc_files, hf_url, num_samples=30, bucket_name="commoncrawl"):
        self.num_samples = num_samples
        self.bucket_name = bucket_name
        self.warc_files = warc_files
        self.hf_url = hf_url
        self.s3 = boto3.client("s3", region_name="us-west-1")

    def get_random_samples(self):
        dataset = load_dataset(self.hf_url, split="train")
        random_indices = random.sample(range(len(dataset)), self.num_samples)
        random_samples = [dataset[i] for i in random_indices]
        return random_samples

    def download_warc_file(self, warc_path):
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=warc_path)
            return BytesIO(response["Body"].read())
        except Exception as e:
            print(f"Error downloading {warc_path}: {e}")
            return None

    def find_text_by_id(self, warc_file_stream, ids_to_find):
        found_texts = []
        try:
            for record in ArchiveIterator(warc_file_stream):
                warc_id = record.rec_headers.get_header("WARC-Record-ID")
                if warc_id in ids_to_find:
                    text_content = (
                        record.content_stream().read().decode("utf-8", errors="ignore")
                    )
                    found_texts.append({"id": warc_id, "text": text_content})
        except Exception as e:
            print(f"Error processing WARC file: {e}")
        finally:
            if warc_file_stream:
                warc_file_stream.close()
        return found_texts

    def process_warc_file(self, warc_path, ids_to_random):
        print(f"Processing WARC file: {warc_path}")
        warc_file_stream = self.download_warc_file(warc_path)
        if warc_file_stream:
            return self.find_text_by_id(warc_file_stream, ids_to_random)
        return []

    def process_all_warc_files(self, ids_to_random):
        all_texts = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_warc = {
                executor.submit(
                    self.process_warc_file, warc_path, ids_to_random
                ): warc_path
                for warc_path in self.warc_files
            }
            for future in as_completed(future_to_warc):
                warc_path = future_to_warc[future]
                try:
                    found_texts = future.result()
                    if found_texts:
                        all_texts.extend(found_texts)
                except Exception as e:
                    print(f"Error processing {warc_path}: {e}")
        return all_texts

    def calculate_word_match_similarity(self, original_text, refined_text):
        def tokenize_and_filter(text):
            stop_words = set(stopwords.words("english"))
            words = nltk.word_tokenize(text.lower())
            filtered_words = [
                word for word in words if word.isalpha() and word not in stop_words
            ]
            return filtered_words

        original_words = tokenize_and_filter(original_text)
        refined_words = tokenize_and_filter(refined_text)

        original_word_count = Counter(original_words)
        refined_word_count = Counter(refined_words)

        matching_words = sum((original_word_count & refined_word_count).values())

        if len(refined_words) == 0:
            return 0
        match_percentage = (matching_words / len(refined_words)) * 100
        return match_percentage

    def run(self):
        random_samples = self.get_random_samples()
        ids_to_random = {sample["id"] for sample in random_samples}
        all_random_texts = self.process_all_warc_files(ids_to_random)
        sorted_random_samples = sorted(random_samples, key=lambda sample: sample["id"])
        sorted_all_random_texts = sorted(
            all_random_texts, key=lambda found: found["id"]
        )

        selected_texts = [sample["text"] for sample in sorted_random_samples]
        found_texts = [found["text"] for found in sorted_all_random_texts]

        scores = []
        for i in range(min(self.num_samples, len(found_texts))):
            score = self.calculate_word_match_similarity(
                found_texts[i], selected_texts[i]
            )
            scores.append(round(score, 2))
            print(f'Match Score for ID {sorted_random_samples[i]["id"]}: {score:.2f}%')

        return scores
