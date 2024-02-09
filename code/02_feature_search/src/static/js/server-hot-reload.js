// *************************************************************************
// server-hot-reload.js v1.0.5
//
// Server-side hot reload check by Michael Kennedy (https://mkennedy.codes).
// Released under the MIT open source license, 2023.
//
// When the contents of the page change in any way, the page will be reloaded.
//
// Usage:
//
// * Include this file in your "application shell" layout template
//   or directly into any page you'd like to check.
//
// * Call toggleServerReload() within the browser console to pause/resume
//   when you want it to give your server a break. Useful when you want to
//   step through breakpoints and don't want the noise, etc.
//
// * Set the checkIntervalInMs time to the frequency you need. Usually 1 sec
//   should be fine, but if a page is slow maybe increase the delay.
//

let currentPageHash = "UNKNOWN";
let checkIntervalInMs = 1000;
let active = true;

// *************************************************************************
// When the doc is ready, we'll start checking for changes.
//
document.addEventListener("DOMContentLoaded", function () {
    console.log("Server hot reload active at " + new Date().toLocaleTimeString() + ". Watching for changes ...");
    const url = document.location.href;

    setInterval(() => downloadHtml(url).then(reloadIfNecessary), checkIntervalInMs);
});


// *************************************************************************
// Called on every page content check (interval is checkIntervalInMs milliseconds).
//
function reloadIfNecessary(html) {
    if (!active) {
        return;
    }

    if (html == null || html.length === 0) {
        console.log("Something went wrong with server hot-reload check... Trying again at interval.")
        return
    }

    const newHash = hashCode(html);
    if (!newHash) return;
    if (currentPageHash === "UNKNOWN") {
        // Compute the hash since have never seen this response on this URL before (first run).
        currentPageHash = newHash;
        return;
    }

    if (newHash === currentPageHash) {
        return;
    }

    // Something, somewhere in the page has changed. Reload
    console.log("Page change detected, reloading now!")
    window.location.reload();
}

// noinspection JSUnusedGlobalSymbols
function toggleServerReload() {
    active = !active;
    const msg = "Server hot reload is now " + (active ? "ACTIVE" : "PAUSED") + ".";
    //console.log("Server hot reload is now " + (active ? "active" : "paused") + ".");
    return msg;
}

function hashCode(html) {
    let hash = 0, i, chr;
    if (html.length === 0) return hash;
    for (i = 0; i < html.length; i++) {
        chr = html.charCodeAt(i);
        hash = ((hash << 5) - hash) + chr;
        hash |= 0; // Convert to 32bit integer
    }
    return hash;
}

async function downloadHtml(url) {
    if (!active) {
        return null;
    }

    const thisURL = new URL(url)
    thisURL.searchParams.append('server_hot_reload_check', 'true')
    try {
        const request = await fetch(thisURL);
        return request.text();
    } catch (e) {
        return '';
    }
}
