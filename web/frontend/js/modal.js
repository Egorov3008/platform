export const Modal = {
    open(html) {
        document.getElementById('modalContent').innerHTML = html;
        document.getElementById('modalOverlay').classList.add('active');
    },
    close() {
        document.getElementById('modalOverlay').classList.remove('active');
    },
};
