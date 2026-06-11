"""
目前登入租戶的 context (存在 st.session_state)。
所有資料查詢都會用 current_tenant_id() 來限定範圍 (Phase 2 起接入)。
"""
import streamlit as st

_KEY = "tenant_id"


def set_current_tenant(tenant_id: str, email: str = "", role: str = "admin"):
    st.session_state[_KEY] = tenant_id
    st.session_state["tenant_email"] = email
    st.session_state["tenant_role"] = role


def current_tenant_id():
    return st.session_state.get(_KEY)


def clear_tenant():
    for k in (_KEY, "tenant_email", "tenant_role"):
        st.session_state.pop(k, None)


def require_tenant() -> str:
    """回傳目前租戶 id；未登入則 None (呼叫端需先確保已登入)。"""
    return st.session_state.get(_KEY)
