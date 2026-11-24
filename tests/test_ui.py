from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_dashboard_and_text_workflow(tmp_path,monkeypatch):
    monkeypatch.setenv('ACI_DB',str(tmp_path/'ui.db'))
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app/main.py', default_timeout=10).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('New Consultation').run()
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert any('Draft created' in s.value for s in app.success)
    app.sidebar.radio[0].set_value('Transcript and Extraction').run()
    assert not app.exception
    assert app.dataframe
    app.sidebar.radio[0].set_value('SOAP Note').run()
    assert len(app.text_area)==4
    app.sidebar.radio[0].set_value('Validation and Review').run()
    app.text_input[0].set_value('Demo QA').run()
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert any('approved' in s.value for s in app.success)
    app.sidebar.radio[0].set_value('History and Export').run()
    assert not app.exception
