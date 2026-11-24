"""Optional browser verification: run with a Python containing Playwright and Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    output=Path('docs/screenshots')
    output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1100})
        page.goto('http://127.0.0.1:8501')
        page.get_by_text('Clinical documentation, with a source.').wait_for()
        page.screenshot(path=str(output/'dashboard.png'),full_page=True)
        page.get_by_text('New Consultation',exact=True).click()
        page.get_by_text('I confirm this consultation is fictional and contains no real patient information.', exact=True).click()
        page.get_by_role('button',name='Generate documentation',exact=True).click()
        page.get_by_text('Draft created.',exact=False).wait_for()
        page.get_by_text('Transcript and Extraction',exact=True).click()
        page.get_by_text('Clinical findings',exact=True).wait_for()
        page.screenshot(path=str(output/'extraction.png'),full_page=True)
        page.get_by_text('SOAP Note',exact=True).click()
        page.get_by_role('button',name='Save new version and validate').wait_for()
        page.screenshot(path=str(output/'soap.png'),full_page=True)
        page.get_by_text('Validation and Review',exact=True).click()
        page.get_by_label('Reviewer name (fictional demo identity)').fill('Synthetic QA reviewer')
        page.get_by_text('I reviewed all sections and acknowledge the displayed warnings.', exact=True).click()
        page.get_by_role('button',name='Approve this version',exact=True).click()
        page.get_by_text('This version is approved for prototype export.').wait_for()
        page.get_by_text('History and Export',exact=True).click()
        page.get_by_role('button',name='Download PDF').wait_for()
        with page.expect_download() as download:
            page.get_by_role('button',name='Download PDF').click()
        download.value.save_as('runtime/ui-approved-note.pdf')
        page.screenshot(path=str(output/'export.png'),full_page=True)
        page.get_by_text('Dashboard',exact=True).click()
        page.get_by_text('Clinical documentation, with a source.').wait_for()
        page.screenshot(path=str(output/'dashboard.png'),full_page=True)
        browser.close()
    print('Browser flow passed: create, evidence, SOAP, approve and PDF download.')


if __name__=='__main__':
    main()
