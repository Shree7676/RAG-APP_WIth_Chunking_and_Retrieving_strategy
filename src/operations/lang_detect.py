from langdetect import detect
from deep_translator import GoogleTranslator
import logging

logger = logging.getLogger('llm_asker')

def check_and_translate_language(question: str, llm_answer: str) -> tuple[str, str]:
    """
    Check if the question and LLM answer are in the same language.
    If not, translate the answer to match the question's language.
    Return both original and (if needed) translated answers.

    Args:
        question (str): The user's question.
        llm_answer (str): The LLM's original answer.

    Returns:
        str: (original_answer+converted_answer)
                         - If languages match, converted_answer is not added.
                         - If they differ, converted_answer is translated to match question's language.
    """
    try:
        # Detect languages
        question_lang = detect(question)
        answer_lang = detect(llm_answer)
        logger.info(f"Detected question language: {question_lang}, answer language: {answer_lang}")

        # If languages match, return original answer unchanged
        if question_lang == answer_lang:
            logger.info("Languages match, no translation needed")
            return llm_answer

        # If languages differ, translate the answer to match the question's language
        logger.info(f"Languages differ, translating answer from {answer_lang} to {question_lang}")
        translator = GoogleTranslator(source=answer_lang, target=question_lang)
        translated_answer = translator.translate(llm_answer)

        # Handle cases where translation fails or returns empty
        if not translated_answer:
            logger.warning("Translation failed, returning original answer")
            return llm_answer

        logger.info("Translation successful")
        return llm_answer+'/n/n/n'+translated_answer

    except Exception as e:
        logger.error(f"Error in language detection or translation: {str(e)}")
        # Fallback: return original answer if anything goes wrong
        return llm_answer