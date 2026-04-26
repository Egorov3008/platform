import { API } from './api.js';
import { Toast } from './toast.js';

export const Admin = {
    async toggleBlock(tgId, block) {
        try {
            await API.patch(`/admin/users/${tgId}`, { is_blocked: block });
            Toast.success(block ? 'Пользователь заблокирован' : 'Пользователь разблокирован');
            const { Pages } = await import('./pages.js');
            Pages._loadAdminTab('users');
        } catch (err) { Toast.error(err.message); }
    },
    async makeAdmin(tgId) {
        try {
            await API.patch(`/admin/users/${tgId}`, { is_admin: true });
            Toast.success('Пользователь назначен администратором');
            const { Pages } = await import('./pages.js');
            Pages._loadAdminTab('users');
        } catch (err) { Toast.error(err.message); }
    },
    async deleteKey(clientId) {
        if (!confirm('Удалить этот ключ?')) return;
        try {
            await API.delete(`/admin/keys/${clientId}`);
            Toast.success('Ключ удалён');
            const { Pages } = await import('./pages.js');
            Pages._loadAdminTab('keys');
        } catch (err) { Toast.error(err.message); }
    },
};
