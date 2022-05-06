/* AUDIU */
// utilities

var util = {
    mobile: _ => {
        return jQuery.browser.mobile;
    },
    cookie: (id, val, date) => {
        if (Block.is.unset(val))
            document.cookie.split('; ').forEach(cookie => {
                if (cookie.substring(0, id.length) == id)
                    val = cookie.substring(id.length + 1);
            });
        else {
            if (date == '__indefinite__')
                date = 'Fri, 31 Dec 9999 23:59:59 GMT';
            document.cookie =
                id +
                '=' +
                val +
                (Block.is.set(date) ? '; expires=' + date : '');
        }
        return Block.is.unset(val) ? null : val;
    },
    delete_cookie: id => {
        util.cookie(id, '', 'Thu, 01 Jan 1970 00:00:00 GMT');
    },
    sha256: (str, callback) => {
        if (callback) callback(window.sha256(str));
    },
    sha256_secure: (str, callback) => {
        const msgUint8 = new TextEncoder("utf-8").encode(str);
        const hashBuffer_promise = crypto.subtle.digest('SHA-256', msgUint8);
        hashBuffer_promise.then(hashBuffer => {
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            if (callback) callback(hashHex);
        });
    }, // https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest
    lpad: (s, width, char) => {
        return s.length >= width
            ? s
            : (new Array(width).join(char) + s).slice(-width);
    }, // https://stackoverflow.com/questions/10841773/javascript-format-number-to-day-with-always-3-digits
    capitalize: word => {
        return word.charAt(0).toUpperCase() + word.slice(1);
    },
    duration_desc: (last_timestamp, forward = false) => {
        if (last_timestamp < 0) return "";
        var ending_tag = forward ? '' : ' ago'
        var now = Date.now();
        var deltaSec = parseInt(now / 1000) - parseInt(last_timestamp / 1000);
        if (forward) deltaSec = -1 * deltaSec;
        if (deltaSec < 0) deltaSec = 0;
        var outputString = "";
        if (deltaSec < 5) {
            outputString += "now";
        } else if (deltaSec < 60) {
            outputString += `${parseInt(Math.floor(parseFloat(deltaSec) / 5.0) * 5.0)} seconds${ending_tag}`;
        } else if (deltaSec < 3600) {
            var mins = parseInt(deltaSec / 60);
            outputString += `${mins} minute${mins == 1 ? '' : 's'}${ending_tag}`;
        } else if (deltaSec < 86400) {
            var hrs = parseInt(deltaSec / 3600);
            outputString += `${hrs} hour${hrs == 1 ? '' : 's'}${ending_tag}`;
        } else if (deltaSec < 604800) {
            var days = parseInt(deltaSec / 86400);
            outputString += `${days} day${days == 1 ? '' : 's'}${ending_tag}`;
        } else {
            var weeks = parseInt(deltaSec / 604800);
            outputString += `${weeks} week${weeks == 1 ? '' : 's'}${ending_tag}`;
        }
        return outputString;
    },
    rand_int: (low, high) => {
        // inclusive
        return (Math.floor(Math.random() * (high - low + 1)) + low);
    },
    sort_compare_newest_first: (a, b, field = 'ts_updated') => {
        return a[field] > b[field] ? -1 : 1;
    },
    sort_compare_oldest_first: (a, b, field = 'ts_updated') => {
        return a[field] < b[field] ? -1 : 1;
    }
};