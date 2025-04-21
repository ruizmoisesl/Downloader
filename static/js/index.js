const DISPLAY_STATES = {
    NONE: 'none',
    FLEX: 'flex'
};

const MENU_STATES = {
    HIDDEN: 'hidden',
    VISIBLE: 'visible'
};

class MenuHandler {
    constructor() {
        this.menu = document.querySelector('.menu');
        this.setupMenuButtons();
    }

    setupMenuButtons() {
        ['menu-black', 'menu-white'].forEach(id => {
            document.getElementById(id)?.addEventListener('click', () => this.toggleMenu());
        });
    }

    toggleMenu() {
        this.menu.classList.toggle(MENU_STATES.HIDDEN);
        this.menu.classList.toggle(MENU_STATES.VISIBLE);
    }

    hideMenu() {
        this.menu.classList.remove(MENU_STATES.VISIBLE);
        this.menu.classList.add(MENU_STATES.HIDDEN);
    }
}

class FormHandler {
    constructor() {
        this.loginModal = new bootstrap.Modal(document.getElementById('login-form'));
        this.registerModal = document.getElementById('register-form');
        this.setupFormButtons();
    }

    setupFormButtons() {
        document.getElementById('login-button')?.addEventListener('click', () => {
            this.registerModal.hide(); 
            this.loginModal.show();
        });

        document.getElementById('register-button')?.addEventListener('click', () => {
            this.loginModal.hide();
            this.registerModal.show();
        });
    }
}

class NavigationHandler {
    constructor() {
        this.setupLogout();
        this.setupDownloader();
    }

    setupLogout() {
        document.getElementById('logout')?.addEventListener('click', 
            () => window.location.href = '/logout');
    }

    setupDownloader() {
        document.getElementById('downloader')?.addEventListener('change', 
            (e) => window.location.href = e.target.value);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.menuHandler = new MenuHandler();
    new FormHandler();
    new NavigationHandler();
});
