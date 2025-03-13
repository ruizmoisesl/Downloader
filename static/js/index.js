const button = document.getElementById('menu-black');
const button2 = document.getElementById('menu-white');
const menu = document.querySelector('.menu');

button.addEventListener('click', () => {
    if (menu.classList.contains('hidden')){
        menu.classList.remove('hidden')
        menu.classList.add('visible')
    }
    else{
        menu.classList.remove('visible')
        menu.classList.add('hidden')
    }
})

button2.addEventListener('click', () => {
    if (menu.classList.contains('hidden')){
        menu.classList.remove('hidden')
        menu.classList.add('visible')
    }
    else{
        menu.classList.remove('visible')
        menu.classList.add('hidden')
    }
})