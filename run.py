from flask import Flask, render_template, url_for, request, session, redirect
from flask import current_app as app, flash, redirect, render_template, session
from flask_login import LoginManager, UserMixin, current_user, login_required, logout_user
from flask_pymongo import PyMongo
from flask_bootstrap import Bootstrap
from flask_nav import Nav
from flask_nav.elements import Navbar, View, Subgroup
from flask_json import FlaskJSON, JsonError, json_response
from grammarbot import GrammarBotClient
from googletrans import Translator
from nltk.tokenize import word_tokenize, sent_tokenize
import gensim
import nltk
import numpy as np
import pandas as pd
import bcrypt

app = Flask(__name__)
app.secret_key = 'CEOTeamCode'
app.config['MONGO_DBNAME'] = 'fyp'
app.config['MONGO_URI'] = 'mongodb+srv://admin:admin@cluster0-gengr.mongodb.net/fyp?retryWrites=true&w=majority'
Bootstrap(app)
nav = Nav()
mongo = PyMongo(app)
json = FlaskJSON(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user():
    return session['username']


@nav.navigation()
def mynavbar():
    if session.get('logged_in'):
        username = load_user()
        return Navbar(
            'Essay.Py',
            View('Welcome back, ' + username, 'home'),
            View('Write Anything Now', 'writing'),
            View('Write A Letter Now', 'letter'),
        )
    else:
        return Navbar(
            'Essay.Py',
            View('Login ', 'home'),
            View('Register', 'register'),
            View('Write Now', 'writing'),
            View('Write A Letter Now', 'letter'),
        )


nav.init_app(app)


@json.error_handler
def error_handler(e):
    # e - JsonError.
    return json_response(401, text='Something wrong.')


@app.route('/')
def index():
    return redirect(url_for('home'))


@app.route('/home')
def home():
    if session.get('logged_in'):
        # return 'You are logged in as ' + session['username']
        users = mongo.db.users
        login_user = users.find_one({'name': session['username']})
        lastSubmission = login_user['result']
        text = lastSubmission['originalText']
        mistakeArray = lastSubmission['mistakes']
        return render_template('user.html', name=session['username'], lastSubmissionText=text, mistakeList=mistakeArray)
    else:
        return render_template('index.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    users = mongo.db.users
    login_user = users.find_one({'name': request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_user['password']) == login_user['password']:
            session['logged_in'] = True
            session['username'] = request.form['username']
            return redirect(url_for('index'))

    return 'Invalid username or password'


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt())
            users.insert({'name': request.form['username'], 'password': hashpass,
                          'result': {'originalText': 'noSubmission', "mistakes": []}})
            session['username'] = request.form['username']
            return redirect(url_for('index'))

        return 'That username already exists!'

    return render_template('register.html')


@app.route('/logout', methods=['GET'])
def logout():
    session['logged_in'] = False
    logout_user()
    if session.get('was_once_logged_in'):
        # prevent flashing automatically logged out message
        del session['was_once_logged_in']
    flash('You have successfully logged yourself out.')
    return redirect('/home')


@app.route('/writing', methods=['POST', 'GET'])
def writing():
    if session.get('logged_in'):
        return render_template('writing.html')
    else:
        return redirect('/home')


@app.route('/letter', methods=['POST', 'GET'])
def letter():
    if session.get('logged_in'):
        return render_template('letter.html')
    else:
        return redirect('/home')


translator = Translator()

checker = GrammarBotClient(api_key='KS9C5N3Y')


def paraphrased(in_text):
    phrased = []
    for i in ['ko', 'ja', 'el', 'fr', 'tl', 'ar', 'ht', 'af', 'sq', 'am']:
        par_text = translator.translate(in_text, dest=i).text
        phrased.append(translator.translate(par_text, dest='en').text.capitalize())
    t = [i for i in phrased if i.lower() != in_text.lower()]
    return "No possible phrases" if not list(set(t)) else list(set(t))


def first_check(text):
    correction_list = []

    for i in checker.check(text).matches:
        correction_list.append(i.message)

    submission = {"originalText": text, "mistakes": correction_list}
    return submission


def grammar_check(alist):
    final_list = []
    # print(alist)
    for i in alist:
        x = [j.corrections for j in checker.check(i).matches]
        if len(x) < 1:
            final_list.append(i)
        else:
            final_list.append(x)
    return final_list


def formatcheck(format):
    mistakes = []
    if not ("Dear" in format[0] or "Hi" in format[0]):
        mistakes.append("Incorrect greeting.")
    elif not ("Peter" in format[0] or "Johnson" in format[0]):
        mistakes.append("Wrong recipient")

    if not ("Regards" in format[1] or "Best Wishes" in format[1] or "Yours sincerely" in format[1]
            or "Yours truly" in format[1] or "Thank" in format[1] or "Cordially" in format[1]):
        if ("Love" in format[1] or "Cheers" in format[1] or "Ciao" in format[1] or "Always" in format[1]):
            mistakes.append("Overly casual. Mind your formality in business letter.")
        elif ("Yours faithfully" in format[1]):
            mistakes.append("You know who your boss is. Use \'Regards\' or \'Yours sincerely\' instead.")
        else:
            mistakes.append("No closing in your email.")

    return mistakes



def similarity(answer):
    marking = "The meeting time is changed from 10am to 3pm. " \
              "Because of the request from Ms Jane Wood. " \
              "The meeting will be on Friday."
    markingtext = []
    markingtokens = sent_tokenize(marking)
    for line in markingtokens:
        markingtext.append(line)

    gen_docs = [[w.lower() for w in word_tokenize(text)]
                for text in markingtext]

    dictionary = gensim.corpora.Dictionary(gen_docs)
    corpus = [dictionary.doc2bow(gen_doc) for gen_doc in gen_docs]
    tf_idf = gensim.models.TfidfModel(corpus)
    sims = gensim.similarities.Similarity('workdir/', tf_idf[corpus],
                                          num_features=len(dictionary))

    answertext = []
    answertokens = sent_tokenize(answer)
    for line in answertokens:
        answertext.append(line)

    avg_similarity = []
    for line in answertext:
        query_doc = [w.lower() for w in word_tokenize(line)]
        query_doc_bow = dictionary.doc2bow(query_doc)
        query_doc_tf_idf = tf_idf[query_doc_bow]
        print('Comparing Result:', sims[query_doc_tf_idf])
        sum_of_sims = (np.sum(sims[query_doc_tf_idf], dtype=np.float32))
        avg = sum_of_sims / len(markingtext)
        print(f'avg: {sum_of_sims / len(markingtext)}')
        avg_similarity.append(avg)
    total_avg = np.sum(avg_similarity, dtype=np.float)
    print(total_avg)

    percentage_of_similarity = round(float(total_avg) * 100)
    if percentage_of_similarity >= 100:
        percentage_of_similarity = 100

    contentmarks = percentage_of_similarity * 1.5
    if contentmarks >=100:
        contentmarks = 100

    return contentmarks

@app.route('/get_data', methods=['POST'])
def get_data():
    if request.method == 'POST':
        users = mongo.db.users
        text = request.form['nlg']
        sentence_list = sent_tokenize(text)
        grammarcheck = first_check(text)
        query = {'name': session['username']}
        result = {"$set": {"result": grammarcheck}}
        users.update_one(query, result)
        trans = paraphrased(text)
        altertext = grammar_check(trans)
        similarity(text)
    return render_template('suggestions.html', your_list=altertext, prediction=[text, altertext, len(altertext)])

@app.route('/marking', methods=['POST'])
def marking():
    if request.method == 'POST':
        format = []
        text = request.form['nlg']
        allmistakes=[]

        users = mongo.db.users
        format.append(request.form['recipient'])
        format.append(request.form['closing'])
        formatmistakes = formatcheck(format)
        for f in formatmistakes:
            allmistakes.append(f)
        if len(formatmistakes) == 0:
            formatmarks = 20
        elif len(formatmistakes) == 1:
            formatmarks = 10
        else:
            formatmarks = 0

        grammarcheck = first_check(text)
        grammarmistakes = grammarcheck['mistakes']
        for g in grammarmistakes:
            allmistakes.append(g)
        if len(grammarmistakes) == 0:
            grammarmarks = 20
        elif len(grammarmistakes) == 1:
            grammarmarks = 15
        elif len(grammarmistakes) == 2:
            grammarmarks = 10
        else:
            grammarmarks = 0

        contentmarks = similarity(text) * 0.6
        totalmarks = formatmarks + grammarmarks + contentmarks

        query = {'name': session['username']}
        r = {"originalText": "Letter", "mistakes": allmistakes}
        result = {"$set": {"result": r}}
        users.update_one(query, result)

        return render_template('result.html', totalscore=totalmarks, contentscore=contentmarks,
                               grammarscore=grammarmarks, formatscore=formatmarks, mistakeList=allmistakes)



if __name__ == '__main__':
    app.run(debug=True)
