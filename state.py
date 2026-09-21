"""
Centralized session_state keys so they're never hand-typed (and typo'd)
across multiple UI files.
"""
import streamlit as st

RESULTS_KEY = "results"
CONFIG_KEY = "config"


def get_results():
    return st.session_state.get(RESULTS_KEY)


def get_config():
    return st.session_state.get(CONFIG_KEY)


def set_results(results):
    st.session_state[RESULTS_KEY] = results


def set_config(config: dict):
    st.session_state[CONFIG_KEY] = config
