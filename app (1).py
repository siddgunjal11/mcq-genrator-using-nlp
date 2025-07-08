# app.py
from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
import spacy
from collections import Counter
import random
from PyPDF2 import PdfReader
import os

app = Flask(__name__, template_folder='templates')
Bootstrap(app)

# Load English tokenizer, tagger, parser, NER, and word vectors
nlp = spacy.load("en_core_web_sm")

def generate_mcqs(text, num_questions=5):
    if not text:
        return []

    # Process the text with spaCy
    doc = nlp(text)

    # Extract sentences from the text
    sentences = [sent.text for sent in doc.sents]

    # Ensure that the number of questions does not exceed the number of sentences
    num_questions = min(num_questions, len(sentences))

    # Randomly select sentences to form questions
    selected_sentences = random.sample(sentences, num_questions)

    mcqs = []

    for sentence in selected_sentences:
        sent_doc = nlp(sentence)

        # Extract named entities and nouns
        entities_and_nouns = [ent.text for ent in sent_doc.ents] + \
                             [token.text for token in sent_doc if token.pos_ == "NOUN"]

        # Ensure there are enough options to generate MCQs
        if len(entities_and_nouns) < 4:
            continue

        subject = random.choice(entities_and_nouns)

        # Generate question stem by masking the subject
        question_stem = sentence.replace(subject, "______")

        # Create distractors
        distractors = list(set(entities_and_nouns) - {subject})

        if len(distractors) < 3:
            distractors += ["[Distractor]"] * (3 - len(distractors))

        random.shuffle(distractors)
        options = [subject] + distractors[:3]
        random.shuffle(options)

        correct_answer = chr(65 + options.index(subject))  # 'A', 'B', 'C', 'D'
        mcqs.append((question_stem, options, correct_answer))

    return mcqs[:num_questions]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = ""

        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            for file in files:
                if file.filename.endswith('.pdf'):
                    text += process_pdf(file)
                elif file.filename.endswith('.txt'):
                    text += file.read().decode('utf-8')
        else:
            text = request.form['text']

        num_questions = int(request.form['num_questions'])
        mcqs = generate_mcqs(text, num_questions=num_questions)
        mcqs_with_index = [(i + 1, mcq) for i, mcq in enumerate(mcqs)]
        return render_template('mcqs.html', mcqs=mcqs_with_index)

    return render_template('index.html')

def process_pdf(file):
    text = ""
    pdf_reader = PdfReader(file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

@app.route('/submit', methods=['POST'])
def submit():
    correct_count = 0
    total_questions = int(request.form.get('total_questions', 0))

    for index in range(1, total_questions + 1):
        user_answer = request.form.get(f'q{index}')
        correct_answer = request.form.get(f'correct_answer_{index}')
        if user_answer == correct_answer:
            correct_count += 1

    score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    return render_template('results.html', score=score_percentage, correct_count=correct_count, total_questions=total_questions)

if __name__ == '__main__':
    app.run(debug=True)
