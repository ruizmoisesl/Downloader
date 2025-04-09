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
        this.forms = {
            login: document.getElementById('login-form'),
            register: document.getElementById('register-form')
        };
        this.setupFormButtons();
    }

    setupFormButtons() {
        // Botones principales
        ['login', 'register'].forEach(type => {
            document.getElementById(`${type}-button`)?.addEventListener('click', 
                () => this.toggleForm(type));
        });

        // Botón de login en menú
        document.getElementById('login-button2')?.addEventListener('click', 
            () => this.showLoginFromMenu());
    }

    toggleForm(type) {
        const isHidden = this.forms[type].style.display === DISPLAY_STATES.NONE;
        this.forms[type].style.display = isHidden ? DISPLAY_STATES.FLEX : DISPLAY_STATES.NONE;
        
        // Ocultar el otro formulario
        const otherType = type === 'login' ? 'register' : 'login';
        this.forms[otherType].style.display = DISPLAY_STATES.NONE;
    }

    showLoginFromMenu() {
        if (this.forms.login.style.display === DISPLAY_STATES.NONE) {
            this.forms.login.style.display = DISPLAY_STATES.FLEX;
            menuHandler.hideMenu();
        }
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

// Inicialización cuando el DOM está listo
window.addEventListener('DOMContentLoaded', () => {
    window.menuHandler = new MenuHandler();
    new FormHandler();
    new NavigationHandler();
});

