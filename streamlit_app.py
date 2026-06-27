"""Streamlit Community Cloud entrypoint.

Set this file as the app's main module when deploying. Keeping it at the repo root
means ``import breachlens`` resolves without any path hacks.
"""

from app.ui import render

if __name__ == "__main__":
    render()
else:  # Streamlit executes the module directly, so render on import too.
    render()
