export const Logger = {
    _enabled: true,
    _groupDepth: 0,

    _prefix(group) {
        const indent = '  '.repeat(this._groupDepth);
        const ts = new Date().toLocaleTimeString('ru-RU');
        return `[${ts}]${indent} [${group}]`;
    },

    log(group, ...args) {
        if (this._enabled) console.log(this._prefix(group), ...args);
    },

    group(group, label) {
        if (this._enabled) {
            console.groupCollapsed(`${this._prefix(group)} ${label}`);
            this._groupDepth++;
        }
    },

    groupEnd() {
        if (this._enabled && this._groupDepth > 0) {
            console.groupEnd();
            this._groupDepth--;
        }
    },

    warn(group, ...args) {
        if (this._enabled) console.warn(this._prefix(group), ...args);
    },

    error(group, ...args) {
        if (this._enabled) console.error(this._prefix(group), ...args);
    },

    info(group, ...args) {
        if (this._enabled) console.info(this._prefix(group), ...args);
    },
};
