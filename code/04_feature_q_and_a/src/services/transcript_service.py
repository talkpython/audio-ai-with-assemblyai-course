from typing import Iterable

from db.transcripts import TranscriptWord
from services import ai_service


class Sentence:
    __slots__ = ['text', 'time']

    def __init__(self, text: str, time: float):
        self.text = text
        self.time = time


transcript_cache: dict[(str, int): list[Sentence]] = {}


async def transcript_text_for_episode(podcast_id: str, episode_number: int) -> list[Sentence]:
    db_tx = await ai_service.transcript_words_for_episode(podcast_id, episode_number)
    if not db_tx or not db_tx.words:
        return []

    sentences = words_to_sentences(db_tx.words)
    return list(sentences)


def words_to_sentences(words: Iterable[TranscriptWord]) -> Iterable[Sentence]:
    active_words = []
    active_sentence = False
    start_time = 0.0

    for word in words:
        if not active_sentence:
            start_time = word.start_in_sec
            active_sentence = True

        active_words.append(word.text)
        if __is_end_of_sentence(word.text):
            sentence_text = ' '.join(active_words).strip()
            sentence = Sentence(sentence_text, start_time)

            active_sentence = False
            start_time = 0.0
            active_words.clear()

            yield sentence


__end_punctuation = {'.', '?', '!'}


def __is_end_of_sentence(text_fragment: str) -> bool:
    if not text_fragment:
        return False

    return text_fragment[-1] in __end_punctuation
