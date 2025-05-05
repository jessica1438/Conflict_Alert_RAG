
import streamlit as st
import csv
import re
import spacy
import sympy
import io
import tiktoken
# from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool
# from langchain.vectorstores import FAISS
# from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize spaCy
nlp = spacy.load('en_core_web_sm')

# Setup session state
if 'knowledge_base' not in st.session_state:
    st.session_state['knowledge_base'] = {}
if 'conflict_log' not in st.session_state:
    st.session_state['conflict_log'] = {}
if 'lc_documents' not in st.session_state:
    st.session_state['lc_documents'] = []
if 'retriever' not in st.session_state:
    st.session_state['retriever'] = None
if 'qa_chain' not in st.session_state:
    st.session_state['qa_chain'] = None

def normalize_expr(expr_str):
    try:
        return str(sympy.simplify(expr_str))
    except:
        return expr_str.strip()

def extract_facts_and_more(text):
    facts = {}

    eq_pattern = re.findall(r'([\w\s\^\*\+/\-]+)=([\w\s\^\*\+/\-]+)', text)
    for left, right in eq_pattern:
        key = normalize_expr(left)
        value = normalize_expr(right)
        facts[key] = value

    is_pattern = re.findall(r'(\b\w+\b) is (\b\w+\b)', text)
    for subject, predicate in is_pattern:
        key = f"FACT_{subject.strip()}"
        value = predicate.strip()
        facts[key] = value

    numeric_pattern = re.findall(r'(\b\w+\b) (has|contains) (\d+)', text)
    for subject, verb, number in numeric_pattern:
        key = f"{subject.strip()}_{verb.strip()}"
        facts[key] = number.strip()

    doc = nlp(text)
    for sent in doc.sents:
        if any(word.lower_ in ["define", "definition", "means", "implies", "denote"] for word in sent):
            facts[f"DEF_{sent[:30]}"] = sent.text.strip()

    return facts

def ingest_csv_document(doc_name, uploaded_file):
    csvfile = io.StringIO(uploaded_file.getvalue().decode('utf-8'))
    reader = csv.DictReader(csvfile)
    columns = reader.fieldnames

    if 'fact' in columns:
        text_column = 'fact'
    elif 'Fact' in columns:
        text_column = 'Fact'
    elif 'text' in columns:
        text_column = 'text'
    else:
        st.warning(f"❌ No suitable text column found in {doc_name}. Skipping.")
        return

    for row in reader:
        text = row.get(text_column, "")
        if not text:
            continue

        extracted = extract_facts_and_more(text)

        for key, new_value in extracted.items():
            if key in st.session_state['knowledge_base']:
                stored_value = st.session_state['knowledge_base'][key]['value']
                if stored_value != new_value:
                    st.session_state['conflict_log'][key] = {
                        'document': doc_name,
                        'key': key,
                        'stored': stored_value,
                        'new': new_value,
                        'stored_sentence': st.session_state['knowledge_base'][key]['source_sentence'],
                        'new_sentence': text
                    }
            else:
                st.session_state['knowledge_base'][key] = {
                    'value': new_value,
                    'source_sentence': text
                }


llm = ChatOpenAI(model="gpt-4")
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

tools = [
    Tool(
        name="ConflictExplainer",
        func=lambda conflict_text: llm.predict(
            f"Explain why this is a conflict and what it means for the user: {conflict_text}"
        ),
        description="Explains detected conflicts in human-readable terms."
    )
]
agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description")

st.title("📄 RAG Conflict Detection App")

# --- File upload section ---
uploaded_files = st.file_uploader("Upload CSV Documents", type="csv", accept_multiple_files=True)

if uploaded_files:
    # Reset previous state
    st.session_state['knowledge_base'] = {}
    st.session_state['conflict_log'] = {}
    st.session_state['lc_documents'] = []

    for uploaded_file in uploaded_files:
        doc_name = uploaded_file.name
        ingest_csv_document(doc_name, uploaded_file)

    if st.session_state['conflict_log']:
        st.warning("⚠ Conflict(s) detected between documents!")
        for c in st.session_state['conflict_log'].values():
            st.write(f"- **{c['key']}** conflict between stored '{c['stored']}' and new '{c['new']}' from {c['document']}")

        ignore = st.button("Ignore Warning and Continue")
    else:
        ignore = True

    if ignore:
        lc_documents = []
        for key, entry in st.session_state['knowledge_base'].items():
            lc_documents.append(Document(page_content=f"{key} = {entry['value']}", metadata={"type": "fact"}))
        for c in st.session_state['conflict_log'].values():
            readable_key = c['key'].replace('FACT_', '').replace('_', ' ').strip()
            conflict_text = (
                f"The document '{c['document']}' contains a conflict about '{readable_key}': "
                f"one source states: '{c['stored_sentence']}', while another states: '{c['new_sentence']}'."
            )
            lc_documents.append(Document(page_content=conflict_text, metadata={"type": "conflict"}))

        st.session_state['lc_documents'] = lc_documents

        vector_store = FAISS.from_documents(lc_documents, embeddings)
        st.session_state['retriever'] = vector_store.as_retriever()
        st.session_state['qa_chain'] = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=st.session_state['retriever'],
            chain_type="stuff"
        )

# --- Query section ---
if st.session_state['qa_chain']:
    user_input = st.text_input("💬 Ask your question")

    if user_input:
        docs = st.session_state['retriever'].get_relevant_documents(user_input)
        conflict_docs = [d for d in docs if d.metadata['type'] == 'conflict']

        if conflict_docs:
            st.warning("⚠ Conflict detected in retrieved documents!")
            for c in conflict_docs:
                explanation = agent.run(c.page_content)
                st.write(f"- {explanation}")

        # Always provide the answer
        result = st.session_state['qa_chain'].run(user_input)
        st.success(f"🧠 Answer: {result}")
else:
    st.info("📥 Please upload documents first and continue to initialize the system.")


