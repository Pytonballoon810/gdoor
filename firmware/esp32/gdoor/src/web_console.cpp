/*
 * This file is part of the GDoor distribution (https://github.com/gdoor-org).
 * Copyright (c) 2024 GDoor authors.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
#include "defines.h"
#include "web_console.h"

// Console page. Plain HTML/JS without external resources, it polls the log and status endpoints.
static const char CONSOLE_PAGE[] PROGMEM = R"html(<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GDoor Console</title>
<style>
body{font-family:verdana,sans-serif;margin:0 auto;padding:12px;max-width:900px;background:#fff;color:#222}
h1{font-size:1.4em;color:#f60;margin:0 0 8px}
h2{font-size:1.05em;margin:16px 0 6px}
pre{background:#111;color:#ddd;padding:8px;border-radius:4px;overflow:auto;font-size:12px;white-space:pre-wrap;word-break:break-all}
#log{height:50vh}
#busdata{font-family:monospace;padding:6px;width:60%}
button{padding:6px 12px;background:#f60;color:#fff;border:0;border-radius:4px;cursor:pointer}
.muted{color:#777;font-size:.9em}
a{color:#f60}
</style></head><body>
<h1>GDoor Console</h1>
<div class="muted"><a href="/">&larr; Menu</a> &middot; bus messages and events since boot, newest at the bottom</div>
<h2>Log</h2>
<pre id="log"></pre>
<label><input type="checkbox" id="follow" checked> follow</label>
<h2>Send to bus</h2>
<form id="send"><input id="busdata" placeholder="hex bus data, e.g. 020031ECF3EB0060A103C27A3D" autocomplete="off"> <button>Send</button></form>
<div id="sendresult" class="muted"></div>
<h2>Status</h2>
<pre id="status">loading...</pre>
<script>
var next=0,log=document.getElementById('log');
function poll(){fetch('/console/log?since='+next).then(function(r){return r.json()}).then(function(d){
 if(d.next<next){log.textContent='';}
 d.lines.forEach(function(l){log.textContent+=l+'\n'});next=d.next;
 if(document.getElementById('follow').checked)log.scrollTop=log.scrollHeight;
}).catch(function(){}).finally(function(){setTimeout(poll,1000)})}
function status(){fetch('/console/status').then(function(r){return r.json()}).then(function(d){
 document.getElementById('status').textContent=JSON.stringify(d,null,2)}).catch(function(){})
 .finally(function(){setTimeout(status,5000)})}
document.getElementById('send').onsubmit=function(e){e.preventDefault();
 var res=document.getElementById('sendresult');
 fetch('/console/send',{method:'POST',headers:{'X-GDoor-Console':'1','Content-Type':'application/x-www-form-urlencoded'},
  body:'busdata='+encodeURIComponent(document.getElementById('busdata').value)})
 .then(function(r){return r.text().then(function(t){res.textContent=t})})};
poll();status();
</script></body></html>)html";

namespace WEB_CONSOLE { //Namespace as we can only use it once
    WebServer *server = nullptr; // WiFiManager's web server, recreated when the portal restarts
    std::function<String()> status_provider = nullptr;
    bool send_enabled = false;

    String lines[WEB_CONSOLE_LINES]; // Ring buffer of the last log lines
    uint32_t next_id = 0; // Id of the next line, lines[next_id % WEB_CONSOLE_LINES]

    String received_payload; // Bus data from the send form, handed to the main loop
    String empty("");
    bool new_payload = false;

    /** Escapes a string for use inside a JSON string literal */
    String json_escape(const String &in) {
        String out;
        out.reserve(in.length() + 8);
        for (size_t i = 0; i < in.length(); i++) {
            char c = in[i];
            switch (c) {
                case '"': out += "\\\""; break;
                case '\\': out += "\\\\"; break;
                case '\n': out += "\\n"; break;
                case '\r': break;
                case '\t': out += "\\t"; break;
                default:
                    if ((uint8_t)c >= 0x20) {
                        out += c;
                    }
            }
        }
        return out;
    }

    /**
     * Adds a line to the console log, prefixed with the uptime in seconds.
     * @param line Text to log, e.g. a bus message JSON
    */
    void log(const String &line) {
        uint32_t ms = millis();
        char prefix[16];
        snprintf(prefix, sizeof(prefix), "%lu.%03lu ", (unsigned long)(ms / 1000), (unsigned long)(ms % 1000));
        lines[next_id % WEB_CONSOLE_LINES] = String(prefix) + line;
        next_id++;
    }

    /** GET /console */
    void handle_page() {
        server->send_P(200, "text/html", CONSOLE_PAGE);
    }

    /** GET /console/log?since=<id>: lines newer than id, as {"next": id, "lines": [...]} */
    void handle_log() {
        uint32_t since = 0;
        if (server->hasArg("since")) {
            since = strtoul(server->arg("since").c_str(), nullptr, 10);
        }
        uint32_t first = next_id > WEB_CONSOLE_LINES ? next_id - WEB_CONSOLE_LINES : 0;
        if (since < first || since > next_id) { // Lines were dropped, or the adapter restarted
            since = first;
        }

        String json = "{\"next\": " + String(next_id) + ", \"lines\": [";
        for (uint32_t id = since; id < next_id; id++) {
            if (id != since) {
                json += ",";
            }
            json += "\"" + json_escape(lines[id % WEB_CONSOLE_LINES]) + "\"";
        }
        json += "]}";
        server->send(200, "application/json", json);
    }

    /** GET /console/status: same JSON as the MQTT status topic */
    void handle_status() {
        if (status_provider == nullptr) {
            server->send(503, "application/json", "{}");
            return;
        }
        server->send(200, "application/json", status_provider());
    }

    /** POST /console/send with busdata=<hex> */
    void handle_send() {
        // A custom header can not be sent cross-origin without a CORS preflight, which is never
        // answered here. So other web pages can not make a visitor's browser send to the bus.
        if (!server->hasHeader("X-GDoor-Console")) {
            server->send(400, "text/plain", "Missing X-GDoor-Console header");
            return;
        }
        if (!send_enabled) {
            server->send(403, "text/plain", "Sending is disabled, enable \"Web console can send to the bus\" in the setup");
            return;
        }
        String busdata = server->arg("busdata");
        busdata.trim();
        if (busdata.length() == 0 || busdata.length() % 2 != 0 || busdata.length() >= MAX_WORDLEN * 2) {
            server->send(400, "text/plain", "Bus data must be an even number of hex digits");
            return;
        }
        for (size_t i = 0; i < busdata.length(); i++) {
            if (!isxdigit((unsigned char)busdata[i])) {
                server->send(400, "text/plain", "Bus data must be an even number of hex digits");
                return;
            }
        }
        received_payload = busdata;
        new_payload = true;
        log("web console: queued " + busdata);
        server->send(200, "text/plain", "Queued " + busdata + ", see log");
    }

    /**
     * Registers the console pages on WiFiManager's web server.
     * Called from WiFiManager's web server callback, every time it creates the server.
    */
    void register_routes(WebServer *webserver) {
        static const char *headers[] = {"X-GDoor-Console"};
        server = webserver;
        server->collectHeaders(headers, 1);
        server->on("/console", HTTP_GET, handle_page);
        server->on("/console/log", HTTP_GET, handle_log);
        server->on("/console/status", HTTP_GET, handle_status);
        server->on("/console/send", HTTP_POST, handle_send);
    }

    /** Sets the function which builds the status JSON */
    void set_status_provider(std::function<String()> provider) {
        status_provider = provider;
    }

    /** Allows or forbids sending to the bus from the console */
    void set_send_enabled(bool enabled) {
        send_enabled = enabled;
    }

    /**
     * Bus data entered in the console, to be sent by the main loop.
     * @return String, empty if nothing was entered since the last call.
    */
    String& receive() {
        if (new_payload) {
            new_payload = false;
            return received_payload;
        }
        return empty;
    }
};
