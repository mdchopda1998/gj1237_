import streamlit as st

from zone_params_config import DEFAULT_ZONE_PARAMS, PARAM_META
from ui.style import icon_span


def _session_key(param_key: str) -> str:
    return f"zp_{param_key}"


def render_right_panel_org() -> dict:
    """
    Right-side "Strategy Parameters" control panel: one widget per
    hard-coded constant in the zone-detection/scoring pipeline
    (identity_zones_with_multibase and its helpers), defaulted to
    whatever that constant's literal value already was in the backend.
    Returns the live dict of values, in the exact shape
    smc_backend.identity_zones_with_multibase(**zone_params) / 
    calculate_trade_score(weekly_trend_window=...) expect.
    """
    st.markdown(
        f"##### {icon_span('tune', size=16)} Strategy Parameters",
        unsafe_allow_html=True,
    )
    st.caption("Hard-coded zone-detection & scoring constants - edit and re-run.")

    with st.container(border=True):
        if st.button("Reset to defaults", icon=":material/restart_alt:", use_container_width=True):
            for key, *_ in PARAM_META:
                st.session_state[_session_key(key)] = DEFAULT_ZONE_PARAMS[key]
            st.rerun()

        values = {}
        for key, label, help_text, lo, hi, step, kind in PARAM_META:
            skey = _session_key(key)
            default_val = DEFAULT_ZONE_PARAMS[key]
            kwargs = {} if skey in st.session_state else {"value": default_val}

            if kind == "slider_int":
                values[key] = st.slider(
                    label, min_value=int(lo), max_value=int(hi), step=int(step),
                    key=skey, help=help_text, **kwargs,
                )
            elif kind == "slider_float":
                values[key] = st.slider(
                    label, min_value=float(lo), max_value=float(hi), step=float(step),
                    key=skey, help=help_text, **kwargs,
                )
            elif kind == "checkbox":
                values[key] = st.checkbox(
                    label, key=skey, help=help_text, **kwargs,
                )
            else:
                values[key] = st.number_input(
                    label, key=skey, help=help_text, **kwargs,
                )

    return values


def render_right_panel() -> dict:
    """
    Right-side "Strategy Parameters" control panel: wrapped in a collapsible 
    expander to allow users to hide/show it dynamically.
    """
    # Wrap everything in an expander component to match the collapsing behaviour of the sidebar
    with st.expander(f"{icon_span('tune', size=16)} Strategy Parameters", expanded=True):
        st.caption("Hard-coded zone-detection & scoring constants - edit and re-run.")

        with st.container(border=True):
            if st.button("Reset to defaults", icon=":material/restart_alt:", use_container_width=True):
                for key, *_ in PARAM_META:
                    st.session_state[_session_key(key)] = DEFAULT_ZONE_PARAMS[key]
                st.rerun()

            values = {}
            for key, label, help_text, lo, hi, step, kind in PARAM_META:
                skey = _session_key(key)
                default_val = DEFAULT_ZONE_PARAMS[key]
                kwargs = {} if skey in st.session_state else {"value": default_val}

                if kind == "slider_int":
                    values[key] = st.slider(
                        label, min_value=int(lo), max_value=int(hi), step=int(step),
                        key=skey, help=help_text, **kwargs,
                    )
                elif kind == "slider_float":
                    values[key] = st.slider(
                        label, min_value=float(lo), max_value=float(hi), step=float(step),
                        key=skey, help=help_text, **kwargs,
                    )
                elif kind == "checkbox":
                    values[key] = st.checkbox(
                        label, key=skey, help=help_text, **kwargs,
                    )
                else:
                    values[key] = st.number_input(
                        label, key=skey, help=help_text, **kwargs,
                    )

    # Note: If the expander is collapsed, this still returns the fallback state 
    # value mappings to ensure backend functionality does not break.
    if not values:
        values = {key: st.session_state.get(_session_key(key), DEFAULT_ZONE_PARAMS[key]) for key, *_ in PARAM_META}
        
    return values
