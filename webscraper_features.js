

function getAllLinks() {
    return Array.from(document.querySelectorAll('a')).map(a => a.href);
}

function getAllImages() {
    return Array.from(document.images).map(img => img.src);
}

function getTextBySelector(selector) {
    return Array.from(document.querySelectorAll(selector)).map(e => e.textContent.trim());
}

function getAttributeBySelector(selector, attr) {
    return Array.from(document.querySelectorAll(selector)).map(e => e.getAttribute(attr));
}

function clickElement(selector) {
    const el = document.querySelector(selector);
    if (el) el.click();
}

function fillInput(selector, value) {
    const el = document.querySelector(selector);
    if (el) el.value = value;
}

function getTableData(selector) {
    const table = document.querySelector(selector);
    if (!table) return [];
    const rows = Array.from(table.rows);
    return rows.map(row => Array.from(row.cells).map(cell => cell.textContent.trim()));
}

function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(() => {
            if (document.querySelector(selector)) {
                clearInterval(interval);
                resolve(true);
            }
        }, 100);
        setTimeout(() => {
            clearInterval(interval);
            reject(new Error('Timeout'));
        }, timeout);
    });
}

function scrollToBottom() {
    window.scrollTo(0, document.body.scrollHeight);
}

function scrollToTop() {
    window.scrollTo(0, 0);
}

function getMetaContent(name) {
    const el = document.querySelector(`meta[name='${name}']`);
    return el ? el.content : null;
}

function getCanonicalUrl() {
    const el = document.querySelector("link[rel='canonical']");
    return el ? el.href : null;
}

function getAllScripts() {
    return Array.from(document.scripts).map(s => s.src);
}

function getAllStylesheets() {
    return Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(l => l.href);
}

function getAllForms() {
    return Array.from(document.forms).map(f => f.action);
}

function getFormFields(formSelector) {
    const form = document.querySelector(formSelector);
    if (!form) return [];
    return Array.from(form.elements).map(e => ({ name: e.name, value: e.value }));
}

function simulateMouseOver(selector) {
    const el = document.querySelector(selector);
    if (el) {
        const event = new MouseEvent('mouseover', { bubbles: true });
        el.dispatchEvent(event);
    }
}

function simulateMouseOut(selector) {
    const el = document.querySelector(selector);
    if (el) {
        const event = new MouseEvent('mouseout', { bubbles: true });
        el.dispatchEvent(event);
    }
}

function getElementRect(selector) {
    const el = document.querySelector(selector);
    return el ? el.getBoundingClientRect() : null;
}

function getElementHtml(selector) {
    const el = document.querySelector(selector);
    return el ? el.outerHTML : null;
}

function getElementText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
}

function getElementValue(selector) {
    const el = document.querySelector(selector);
    return el ? el.value : null;
}

function setElementValue(selector, value) {
    const el = document.querySelector(selector);
    if (el) el.value = value;
}

function isElementVisible(selector) {
    const el = document.querySelector(selector);
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetHeight > 0;
}

function getAllButtons() {
    return Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim());
}

function getAllInputs() {
    return Array.from(document.querySelectorAll('input')).map(i => ({ name: i.name, value: i.value }));
}

function getAllSelectOptions(selector) {
    const el = document.querySelector(selector);
    if (!el) return [];
    return Array.from(el.options).map(o => o.value);
}

function selectOption(selector, value) {
    const el = document.querySelector(selector);
    if (el) el.value = value;
}

function getAllCheckboxes() {
    return Array.from(document.querySelectorAll('input[type="checkbox"]')).map(c => ({ name: c.name, checked: c.checked }));
}

function checkCheckbox(selector) {
    const el = document.querySelector(selector);
    if (el) el.checked = true;
}

function uncheckCheckbox(selector) {
    const el = document.querySelector(selector);
    if (el) el.checked = false;
}

function getAllRadioButtons() {
    return Array.from(document.querySelectorAll('input[type="radio"]')).map(r => ({ name: r.name, checked: r.checked }));
}

function selectRadioButton(selector) {
    const el = document.querySelector(selector);
    if (el) el.checked = true;
}

function getAllLinksWithText(text) {
    return Array.from(document.querySelectorAll('a')).filter(a => a.textContent.includes(text)).map(a => a.href);
}

function getAllElementsWithClass(className) {
    return Array.from(document.getElementsByClassName(className));
}

function getAllElementsWithTag(tagName) {
    return Array.from(document.getElementsByTagName(tagName));
}

function getAllElementsWithAttribute(attr) {
    return Array.from(document.querySelectorAll(`[${attr}]`));
}

function getAllIframes() {
    return Array.from(document.querySelectorAll('iframe')).map(f => f.src);
}

function getAllVideos() {
    return Array.from(document.querySelectorAll('video')).map(v => v.src);
}

function getAllAudios() {
    return Array.from(document.querySelectorAll('audio')).map(a => a.src);
}

function getAllParagraphs() {
    return Array.from(document.querySelectorAll('p')).map(p => p.textContent.trim());
}

function getAllHeadings() {
    return Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => h.textContent.trim());
}

function getAllLists() {
    return Array.from(document.querySelectorAll('ul, ol')).map(l => l.innerHTML);
}

function getAllTableRows(selector) {
    const table = document.querySelector(selector);
    if (!table) return [];
    return Array.from(table.rows);
}

function getDocumentTitle() {
    return document.title;
}

function getDocumentURL() {
    return document.URL;
}

function getDocumentDomain() {
    return document.domain;
}

function getDocumentReferrer() {
    return document.referrer;
} 