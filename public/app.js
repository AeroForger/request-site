import {
    projects
} from './projects.js';
const drawings = {
    compiler: '<path d="m43 28-24 27 24 27m64-54 24 27-24 27M88 15 62 95"/>',
    hop: '<path d="m20 77 27-44 28 44 28-44 27 44M20 90h110"/><circle cx="47" cy="33" r="5"/><circle cx="103" cy="33" r="5"/>',
    string: '<path d="M10 56c20-65 30 65 50 0s30 65 50 0 25 0 30 0M10 56h130"/><circle cx="10" cy="56" r="3"/><circle cx="140" cy="56" r="3"/>',
};
const externalIcon = '<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 17 17 7M7 7h10v10"/></svg>';
const list = document.querySelector('#project-list');
projects.forEach((project, index) => {
    const card = document.createElement('article');
    card.className = 'project-card';
    // Artwork comes only from this local, fixed dictionary.
    card.innerHTML = `<div class="project-art" aria-hidden="true" data-label="AF / ${String(index + 1).padStart(2, '0')}"><svg viewBox="0 0 150 110" fill="none" stroke="#b7ae8b" stroke-width="1.2">${drawings[project.artwork]}</svg></div><div class="project-content"><div class="project-title"><h3></h3><span class="project-number">0${index + 1}</span></div></div>`;
    card.querySelector('h3').textContent = project.name;
    const content = card.querySelector('.project-content');
    if (project.description) {
        const p = document.createElement('p');
        p.textContent = project.description;
        content.append(p);
    }
    if (project.technologies.length || project.status) {
        const meta = document.createElement('div');
        meta.className = 'project-meta';
        for (const label of [...project.technologies, project.status].filter(Boolean)) {
            const tag = document.createElement('span');
            tag.textContent = label;
            meta.append(tag);
        }
        content.append(meta);
    }
    if (project.github && /^https:\/\/github\.com\//.test(project.github)) {
        const link = document.createElement('a');
        link.className = 'text-link project-link';
        link.href = project.github;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'View on GitHub';
        link.insertAdjacentHTML('beforeend', externalIcon);
        link.setAttribute('aria-label', `View ${project.name} on GitHub (opens in a new tab)`);
        content.append(link);
    }
    list.append(card);
});
const menu = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');

function closeMenu() {
    menu.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('open');
}
menu.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    navigation.classList.toggle('open', open);
});
navigation.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeMenu();
});
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && navigation.classList.contains('open')) {
        closeMenu();
        menu.focus();
    }
});
const form = document.querySelector('#request-form');
const description = form.elements.description;
description.addEventListener('input', () => {
    document.querySelector('#character-count').textContent = `${description.value.length.toLocaleString()} / 5,000`;
});
let submitting = false;
form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitting || !form.reportValidity()) return;
    submitting = true;
    const button = form.querySelector('button[type="submit"]');
    const status = document.querySelector('#form-status');
    button.disabled = true;
    button.textContent = 'Sending...';
    form.setAttribute('aria-busy', 'true');
    status.textContent = '';
    status.className = '';
    try {
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(Object.fromEntries(new FormData(form))),
            signal: AbortSignal.timeout(20000)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Unable to send your request. Please try again shortly.');
        status.textContent = "Request sent. I'll contact you if I'm interested.";
        form.reset();
        document.querySelector('#character-count').textContent = '0 / 5,000';
    } catch (error) {
        status.className = 'error';
        status.textContent = error.name === 'TypeError' || error.name === 'TimeoutError' || error.name === 'SyntaxError' ? 'Connection interrupted. Your details are saved in the form; please try again shortly.' : error.message;
    } finally {
        submitting = false;
        button.disabled = false;
        button.innerHTML = `Send Request ${externalIcon}`;
        form.removeAttribute('aria-busy');
    }
});
