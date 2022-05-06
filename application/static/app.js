/* AUDIU */
// web client

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
                data: body,
                dataType: "json",
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
    },
    main: {
        config: {},
        init: (_) => {
            console.clear();
            console.log("[main] loading...");
            setTimeout((_) => {
                app.ui.place_root_block();
                app.ui.block.load(
                    (_) => {
                        app.ui.block.load(
                            (_) => {
                                console.log("[main] blocks loaded");
                                app.ui.init((_) => {
                                    console.log("[main] ready");
                                    setTimeout(app.main.test, app.main.test_delay);
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
