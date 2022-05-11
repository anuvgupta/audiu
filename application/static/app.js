/* AUDIU */
// web client

const ws_debug_port = 8002;

var app = {
    ui: {
        block: null,
        display_modal: {
            disconnected: (_) => {
                bootbox.hideAll();
                setTimeout((_) => {
                    bootbox.confirm({
                        centerVertical: true,
                        title: "Disconnected",
                        message: "Refresh page?",
                        callback: (result) => {
                            if (result) window.location.reload();
                        },
                    });
                }, 200);
            },
            generic_confirm: (title, message, callback) => {
                bootbox.confirm({
                    centerVertical: true,
                    title: `<span class="modal_title">${title}</span>`,
                    message: `${message}`,
                    callback: callback,
                });
            },
            new_project: (_) => {
                bootbox.confirm({
                    centerVertical: true,
                    title: '<span class="modal_title">Create Project</span>',
                    message:
                        `<div id='new_project_display_modal'>` +
                        `<div style="margin: 3px 0;"><span class="modal_text_input_label">Name:</span>&nbsp;` +
                        `<input placeholder="Project Zero" class="modal_text_input" id="np_modal_name_input" type='text' name='np_modal_name'/></div>` +
                        `<div style="margin: 3px 0;"><span class="modal_text_input_label">Identifier:</span>&nbsp;` +
                        `<input placeholder="project-zero" class="modal_text_input" id="np_modal_slug_input" type='text' name='np_modal_slug'/></div>` +
                        `<div style="margin: 3px 0;"><span class="modal_text_input_label">Repository:</span>&nbsp;` +
                        `<input placeholder="https://github.com/u/project-zero" class="modal_text_input" id="np_modal_repo_input" type='text' name='np_modal_repo'/></div>` +
                        `<div style="margin: 3px 0;"><span class="modal_text_input_label">Description:</span>&nbsp;` +
                        `<input placeholder="Lorem ipsum dolor sit amet..." class="modal_text_input" id="np_modal_desc_input" type='text' name='np_modal_desc'/></div>` +
                        `<div style="height: 8px"></div></div>`,
                    callback: (result) => {
                        if (result) {
                            var slug = `${$("#new_project_display_modal #np_modal_slug_input")[0].value
                                }`.trim();
                            var name = `${$("#new_project_display_modal #np_modal_name_input")[0].value
                                }`.trim();
                            var repo = `${$("#new_project_display_modal #np_modal_repo_input")[0].value
                                }`.trim();
                            var desc = `${$("#new_project_display_modal #np_modal_desc_input")[0].value
                                }`.trim();
                            if (slug == "" || name == "") return false;
                            app.ws.api.new_project(slug, name, repo, desc);
                        }
                        return true;
                    },
                });
            },
            new_project_res: (message) => {
                bootbox.confirm({
                    centerVertical: true,
                    title: '<span class="modal_title">Create Project</span>',
                    message: `${message}`,
                    callback: (result) => {
                        if (result) {
                            setTimeout((_) => {
                                app.ws.api.get_projects();
                            }, 100);
                            return true;
                        }
                    },
                });
            },
        },
        place_root_block: (_) => {
            app.ui.block = Block("div", "app");
        },
        init: (callback) => {
            app.ui.block.fill(document.body);
            Block.queries();
            setTimeout((_) => {
                if (app.main.config.target_run_id != '') {
                    app.ui.block.data({
                        target_run_id: app.main.config.target_run_id
                    });
                }
                app.ui.block.css("opacity", "1");
                app.ui.block.on("ready");
                setTimeout(_ => {
                    // enable ripple effect on material-ui buttons after generated and injected by block.js
                    window.componentHandler.upgradeDom();
                }, 100);
            }, 100);
            setTimeout((_) => {
                Block.queries();
                setTimeout((_) => {
                    Block.queries();
                }, 200);
            }, 50);
            callback();
        },
    },
    web: {
        post: (endpoint, body, success, failure) => {
            $.ajax({
                url: endpoint,
                type: "POST",
                data: JSON.stringify(body),
                success: function (data) {
                    console.log(`POST to ${endpoint}`);
                    success(data);
                },
                error: function (xhr, status, error) {
                    console.error(status);
                    console.log(xhr.responseJSON);
                    console.log(error);
                    failure(xhr.responseJSON, error, status);
                },
            });
        },
        get: (endpoint, params, success, failure) => {
            var query_string = util.encode_url_query_params(params);
            var query_url = `${endpoint}?${query_string}`;
            $.ajax({
                url: query_url,
                type: "GET",
                success: function (data) {
                    console.log(`GET to ${query_url}`);
                    success(data);
                },
                error: function (xhr, status, error) {
                    console.error(status);
                    console.log(xhr.responseJSON);
                    console.log(error);
                    failure(xhr.responseJSON, error, status);
                },
            });
        },
        api: {
            generate_recommendations: (selected_model, playlist_selections, genre_selections, callback = null) => {
                for (var p in playlist_selections)
                    playlist_selections[p] = app.main.sp_playlist_link_to_id(playlist_selections[p]);
                for (var g in genre_selections)
                    genre_selections[g] = app.main.reverse_genre_correction(genre_selections[g]);
                app.web.post("model", {
                    selected_model: selected_model,
                    playlist_selections: playlist_selections,
                    genre_selections: genre_selections
                }, (data) => {
                    if (data.success && data.hasOwnProperty('data') && callback)
                        callback(data.data);
                }, (data, error, status) => {
                    console.error(`HTTP request error with "generate_recommendations": ${status}`);
                    // console.log(error);
                    // console.log(data);
                    if (data.hasOwnProperty('message')) {
                        console.log(data.message);
                        app.ui.display_modal.generic_confirm("Recommendations Model Error", `Server Error: ${data.message}`, (s) => { /* console.log(s); */ });
                    }
                });
            },
            check_recommendations_status: (run_id, callback = null) => {
                app.web.get("model", {
                    run_id: run_id,
                }, (data) => {
                    if (data.success && data.hasOwnProperty('data') && callback)
                        callback(data.data);
                }, (data, error, status) => {
                    console.error(`HTTP request error with "generate_recommendations": ${status}`);
                    // console.log(error);
                    // console.log(data);
                    if (data.hasOwnProperty('message')) {
                        console.log(data.message);
                        app.ui.display_modal.generic_confirm("Recommendations Model Error", `Server Error: ${data.message}`, (s) => { /* console.log(s); */ });
                    }
                });
            }
        }
    },
    ws: {
        id: 0,
        socket: null,
        url:
            (location.protocol === 'https:' ? 'wss://' : 'ws://') + document.domain +
            (document.domain == 'localhost' ? `:${ws_debug_port}` : ((location.protocol === 'https:' ? ':443' : ':80') + '/socket')),
        connect: callback => {
            var socket = new WebSocket(app.ws.url);
            socket.addEventListener('open', e => {
                console.log('[ws] socket connected');
                callback();
            });
            socket.addEventListener('error', e => {
                console.log('[ws] socket error ', e.data);
            });
            socket.addEventListener('message', e => {
                var d = e.data;
                if (d != null) {
                    console.log(`[ws] socket received: ${d}`);
                    // var data = {};
                    // data[d.event] = d.data;
                    // app.ui.block.data(data);
                } else {
                    console.log('[ws] socket received:', 'invalid message', e.data);
                }
            });
            socket.addEventListener('close', e => {
                console.log('[ws] socket disconnected');
                app.ui.display_modal.disconnected();
            });
            window.addEventListener('beforeunload', e => {
                // socket.close(1001);
            });
            app.ws.socket = socket;
        },
        send: (data) => {
            console.log('[ws] sending:', data);
            app.ws.socket.send(data);
        },
        api: {
            send_message: (msg) => {
                app.ws.send(msg);
            }
        }
    },
    main: {
        config: {
            url_params: null,
            target_run_id: "",
            dataset: {}
        },
        sp_playlist_link_to_id: (playlist_link_raw) => {
            return playlist_link_raw.split('?si=')[0]
                .replaceAll('https://', '').replaceAll('http://', '')
                .replaceAll('open.spotify.com/playlist/', '');
        },
        genre_correction: (genre) => {
            var genre_replacements = app.main.config.dataset.config.genre_replacements;
            genre = genre.replaceAll('_', ' ');
            for (var genre_repl in genre_replacements)
                genre = genre.replaceAll(genre_repl, genre_replacements[genre_repl]);
            return genre;
        },
        reverse_genre_correction: (genre) => {
            var genre_replacements = app.main.config.dataset.config.genre_replacements;
            for (var genre_repl in genre_replacements)
                genre = genre.replaceAll(genre_replacements[genre_repl], genre_repl);
            genre = genre.replaceAll(' ', '_');
            return genre;
        },
        get_genre_list: () => {
            var remove_item = app.main.config.dataset.config.genre_remove_item;
            var genres_list = app.main.config.dataset.genres.slice(0);
            genres_list.splice(genres_list.indexOf(remove_item), 1);
            for (var g in genres_list)
                genres_list[g] = app.main.genre_correction(genres_list[g]);
            return genres_list;
        },
        get_genre_list_str: () => {
            var remove_item = app.main.config.dataset.config.genre_remove_item;
            var genres_list = app.main.config.dataset.genres.slice(0);
            genres_list.splice(genres_list.indexOf(remove_item), 1);
            genres_list = genres_list.join(', ');
            genres_list = app.main.genre_correction(genres_list);
            return genres_list;
        },
        init: (_) => {
            console.clear();
            console.log("[main] loading...");
            app.main.config.url_params = new URLSearchParams(window.location.search);
            if (window.location.pathname == '/fresh') {
                app.main.config.target_run_id = app.main.config.url_params.get('r')
            }
            console.log("[main] target run = " + app.main.config.target_run_id);
            setTimeout((_) => {
                app.ui.place_root_block();
                app.ui.block.load(
                    (_) => {
                        app.ui.block.load(
                            (_) => {
                                console.log("[main] blocks loaded");
                                console.log("[main] socket connecting");
                                app.ws.connect(_ => {
                                    app.ui.init((_) => {
                                        console.log("[main] ready");
                                        setTimeout(app.main.test, app.main.test_delay);
                                    });
                                });
                            },
                            "app",
                            "jQuery"
                        );
                    },
                    "blocks",
                    "jQuery"
                );
            }, 10);
        },
        test: (_) => {
            console.log("[main] testing...");
            setTimeout((_) => {
                // testing stuff here
            }, 200);
        },
        test_delay: 100,
    },
};

// $(document).ready(app.main.init);
setTimeout(app.main.init, 800);
