/** @odoo-module **/

import { session } from "@web/session";


const originalCookieDesc = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
const originalDocCookieSet = originalCookieDesc.set;
const originalDocCookieGet = originalCookieDesc.get;


function secureCookie(value) {
    if (!session.secure_cookies) {
        return value;
    }
    try {
        let parts = value.split(';').map(part => part.trim());
        let mainPart = parts[0];
        let options = parts.slice(1);

        const cookieName = mainPart.split('=')[0];
        const hasSecure = options.some(opt => opt.toLowerCase() === 'secure');
        const hasSameSite = options.some(opt => opt.toLowerCase().startsWith('samesite='));

        if (!hasSecure) {
            options.push('Secure');
        }

        if (!hasSameSite) {
            options.push(`SameSite=Strict`);
        }
        return [mainPart, ...options].join('; ');
    }
    catch (error) {
        console.error(error);
        return value
    }
}


// Interception document.cookie
Object.defineProperty(Document.prototype, 'cookie', {
    configurable: true,
    get: function() {
        return originalDocCookieGet.call(this);
    },
    set: function(value) {
        const secureValue = secureCookie(value);
        return originalDocCookieSet.call(this, secureValue);
    }
});
