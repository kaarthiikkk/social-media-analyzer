document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const form = document.getElementById("uploadForm");
    const fileInput = document.getElementById("fileInput");
    const dropArea = document.getElementById("dropArea");
    const fileList = document.getElementById("fileList");
    const submitBtn = document.getElementById("submitBtn");
    const clearBtn = document.getElementById("clearFiles");
    const loading = document.getElementById("loading");

    let selectedFiles = [];

    const allowedExtensions = [
        "pdf",
        "png",
        "jpg",
        "jpeg"
    ];

    const MAX_SIZE = 10 * 1024 * 1024;


    /* =====================================================
       FILE HELPERS
    ====================================================== */

    function extension(filename) {
        return filename
            .split(".")
            .pop()
            .toLowerCase();
    }


    function validFile(file) {
        return allowedExtensions.includes(
            extension(file.name)
        );
    }


    function formatSize(bytes) {
        if (bytes < 1024) {
            return `${bytes} B`;
        }

        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }

        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }


    function iconFor(file) {
        return extension(file.name) === "pdf"
            ? "bi-file-earmark-pdf"
            : "bi-file-earmark-image";
    }


    /* =====================================================
       HTML ESCAPING
    ====================================================== */

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    /* =====================================================
       FILE LIST
    ====================================================== */

    function renderFiles() {

        if (!fileList) {
            return;
        }

        fileList.innerHTML = "";

        selectedFiles.forEach((file, index) => {

            const row = document.createElement("div");

            row.className = "file-item";

            row.innerHTML = `
                <div style="
                    display:flex;
                    align-items:center;
                    gap:10px;
                    width:100%;
                ">

                    <div style="
                        width:34px;
                        height:34px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        border-radius:9px;
                        background:#f4f3ff;
                        color:#635bff;
                        flex-shrink:0;
                    ">
                        <i class="bi ${iconFor(file)}"></i>
                    </div>

                    <div style="
                        flex:1;
                        min-width:0;
                    ">

                        <strong style="
                            display:block;
                            overflow:hidden;
                            text-overflow:ellipsis;
                            white-space:nowrap;
                            font-size:.76rem;
                        ">
                            ${escapeHtml(file.name)}
                        </strong>

                        <span style="
                            display:block;
                            margin-top:2px;
                            color:#98a2b3;
                            font-size:.65rem;
                        ">
                            ${formatSize(file.size)}
                        </span>

                    </div>

                    <button
                        type="button"
                        class="remove-file"
                        data-index="${index}"
                        aria-label="Remove file"
                        style="
                            border:0;
                            background:transparent;
                            color:#98a2b3;
                            width:30px;
                            height:30px;
                            border-radius:8px;
                            cursor:pointer;
                        "
                    >
                        <i class="bi bi-x-lg"></i>
                    </button>

                </div>
            `;

            fileList.appendChild(row);
        });


        document
            .querySelectorAll(".remove-file")
            .forEach(button => {

                button.addEventListener(
                    "click",
                    event => {

                        event.preventDefault();
                        event.stopPropagation();

                        const index =
                            Number(button.dataset.index);

                        selectedFiles.splice(
                            index,
                            1
                        );

                        syncInput();
                        renderFiles();
                        updateButton();
                    }
                );
            });


        updateButton();
    }


    /* =====================================================
       SYNC FILE INPUT
    ====================================================== */

    function syncInput() {

        if (!fileInput) {
            return;
        }

        try {

            const transfer = new DataTransfer();

            selectedFiles.forEach(file => {
                transfer.items.add(file);
            });

            fileInput.files = transfer.files;

        } catch (error) {

            console.warn(
                "Could not synchronize file input:",
                error
            );
        }
    }


    /* =====================================================
       ADD FILES
    ====================================================== */

    function addFiles(fileCollection) {

        const files =
            Array.from(fileCollection || []);

        if (!files.length) {
            return;
        }


        const newFiles = [];


        for (const file of files) {

            if (!validFile(file)) {

                alert(
                    `${file.name} is not supported. ` +
                    "Please use PDF, PNG, JPG or JPEG."
                );

                continue;
            }


            if (file.size > MAX_SIZE) {

                alert(
                    `${file.name} is larger than 10 MB.`
                );

                continue;
            }


            const duplicate =
                selectedFiles.some(existing =>
                    existing.name === file.name &&
                    existing.size === file.size &&
                    existing.lastModified ===
                        file.lastModified
                );

            if (duplicate) {
                continue;
            }


            newFiles.push(file);
        }


        const totalSize =
            selectedFiles.reduce(
                (sum, file) =>
                    sum + file.size,
                0
            )
            +
            newFiles.reduce(
                (sum, file) =>
                    sum + file.size,
                0
            );


        if (totalSize > MAX_SIZE) {

            alert(
                "Total upload size must be under 10 MB."
            );

            return;
        }


        selectedFiles.push(
            ...newFiles
        );

        syncInput();
        renderFiles();
        updateButton();
    }


    /* =====================================================
       BUTTON STATE
    ====================================================== */

    function updateButton() {

        if (!submitBtn) {
            return;
        }

        /*
         * Keep the button enabled.
         *
         * The backend will handle the case where
         * no file was selected.
         *
         * This also prevents Safari from getting
         * stuck because of a disabled submit button.
         */

        submitBtn.disabled = false;
    }


    /* =====================================================
       FILE INPUT
    ====================================================== */

    if (fileInput) {

        fileInput.addEventListener(
            "change",
            event => {

                addFiles(
                    event.target.files
                );
            }
        );
    }


    /* =====================================================
       DROP AREA
    ====================================================== */

    if (dropArea) {

        dropArea.addEventListener(
            "click",
            event => {

                /*
                 * Don't trigger another click when the
                 * actual input itself is clicked.
                 */

                if (
                    event.target === fileInput
                ) {
                    return;
                }

                fileInput.click();
            }
        );


        dropArea.addEventListener(
            "keydown",
            event => {

                if (
                    event.key === "Enter" ||
                    event.key === " "
                ) {

                    event.preventDefault();

                    fileInput.click();
                }
            }
        );


        [
            "dragenter",
            "dragover"
        ].forEach(type => {

            dropArea.addEventListener(
                type,
                event => {

                    event.preventDefault();
                    event.stopPropagation();

                    dropArea.classList.add(
                        "dragover"
                    );
                }
            );
        });


        [
            "dragleave",
            "drop"
        ].forEach(type => {

            dropArea.addEventListener(
                type,
                event => {

                    event.preventDefault();
                    event.stopPropagation();

                    dropArea.classList.remove(
                        "dragover"
                    );
                }
            );
        });


        dropArea.addEventListener(
            "drop",
            event => {

                addFiles(
                    event.dataTransfer.files
                );
            }
        );
    }


    /* =====================================================
       CLEAR FILES
    ====================================================== */

    if (clearBtn) {

        clearBtn.addEventListener(
            "click",
            event => {

                event.preventDefault();

                selectedFiles = [];

                if (fileInput) {
                    fileInput.value = "";
                }

                renderFiles();
                updateButton();
            }
        );
    }


    /* =====================================================
       FORM SUBMISSION
       
       IMPORTANT:
       Explicitly submit the form after syncing the
       selected files. This fixes the Safari issue where
       the UI showed "Analyzing..." but Flask never
       received POST /.
    ====================================================== */

    if (form) {

        form.addEventListener(
            "submit",
            function (event) {

                event.preventDefault();


                if (
                    selectedFiles.length === 0 &&
                    (!fileInput ||
                     fileInput.files.length === 0)
                ) {

                    alert(
                        "Please select a file first."
                    );

                    return;
                }


                /*
                 * Make absolutely sure the files are
                 * attached to the real HTML input.
                 */

                syncInput();


                /*
                 * Update button.
                 */

                if (submitBtn) {

                    submitBtn.disabled = true;

                    submitBtn.innerHTML = `
                        <span>Analyzing...</span>
                        <i class="bi bi-arrow-repeat spin-icon"></i>
                    `;
                }


                /*
                 * Show loading panel.
                 */

                if (loading) {

                    loading.classList.remove(
                        "d-none"
                    );
                }


                /*
                 * IMPORTANT:
                 *
                 * Use the native HTML form submit.
                 *
                 * This bypasses JavaScript's submit
                 * event and sends:
                 *
                 * POST /
                 *
                 * multipart/form-data
                 *
                 * files
                 * platform
                 * goal
                 */

                setTimeout(
                    function () {

                        HTMLFormElement
                            .prototype
                            .submit
                            .call(form);

                    },
                    100
                );

            }
        );
    }


    /* =====================================================
       COPY TEXT
    ====================================================== */

    async function copyText(text) {

        if (!text) {
            return;
        }


        try {

            await navigator.clipboard.writeText(
                text
            );

            alert(
                "Copied to clipboard."
            );

        } catch (error) {

            const textarea =
                document.createElement(
                    "textarea"
                );

            textarea.value = text;

            document.body.appendChild(
                textarea
            );

            textarea.select();

            document.execCommand(
                "copy"
            );

            textarea.remove();

            alert(
                "Copied to clipboard."
            );
        }
    }


    /* =====================================================
       GENERIC COPY BUTTONS
    ====================================================== */

    document
        .querySelectorAll(
            "[data-copy-target]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                event => {

                    event.preventDefault();

                    const target =
                        document.getElementById(
                            button.dataset.copyTarget
                        );

                    if (!target) {
                        return;
                    }

                    copyText(
                        target.innerText ||
                        target.textContent
                    );
                }
            );
        });


    /* =====================================================
       COPY HASHTAGS
    ====================================================== */

    const copyHashtags =
        document.getElementById(
            "copyHashtags"
        );

    if (copyHashtags) {

        copyHashtags.addEventListener(
            "click",
            event => {

                event.preventDefault();

                copyText(
                    copyHashtags.dataset.tags
                );
            }
        );
    }


    /* =====================================================
       COPY ALL ENGAGEMENT RECOMMENDATIONS
    ====================================================== */

    const copyEngagement =
        document.getElementById(
            "copyEngagement"
        );

    if (copyEngagement) {

        copyEngagement.addEventListener(
            "click",
            event => {

                event.preventDefault();

                const items =
                    document.querySelectorAll(
                        ".engagement-item"
                    );

                const text =
                    Array.from(items)
                        .map(
                            (item, index) => {

                                const title =
                                    item.querySelector(
                                        ".recommendation-heading strong"
                                    )?.innerText || "";

                                const reason =
                                    item.querySelector(
                                        ".engagement-content > p"
                                    )?.innerText || "";

                                const action =
                                    item.querySelector(
                                        ".recommendation-action span"
                                    )?.innerText || "";

                                return (
                                    `${index + 1}. ${title}\n` +
                                    `Why: ${reason}\n` +
                                    `Action: ${action}`
                                );
                            }
                        )
                        .join("\n\n");

                copyText(text);
            }
        );
    }


    /* =====================================================
       SHOW MORE / LESS
    ====================================================== */

    const toggleCombined =
        document.getElementById(
            "toggleCombined"
        );

    const combinedText =
        document.getElementById(
            "combinedText"
        );

    if (
        toggleCombined &&
        combinedText
    ) {

        toggleCombined.addEventListener(
            "click",
            event => {

                event.preventDefault();

                const expanded =
                    combinedText.classList.toggle(
                        "expanded-scroll"
                    );

                toggleCombined.textContent =
                    expanded
                        ? "Show less"
                        : "Show more";
            }
        );
    }


    /* =====================================================
       EXPORT ANALYSIS
    ====================================================== */

    const exportButton =
        document.getElementById(
            "exportAnalysis"
        );

    if (exportButton) {

        exportButton.addEventListener(
            "click",
            event => {

                event.preventDefault();

                const dataElement =
                    document.getElementById(
                        "analysisData"
                    );

                if (!dataElement) {
                    return;
                }


                try {

                    const data =
                        JSON.parse(
                            dataElement.textContent
                        );

                    const blob =
                        new Blob(
                            [
                                JSON.stringify(
                                    data,
                                    null,
                                    2
                                )
                            ],
                            {
                                type:
                                    "application/json"
                            }
                        );


                    const url =
                        URL.createObjectURL(
                            blob
                        );


                    const a =
                        document.createElement(
                            "a"
                        );

                    a.href = url;

                    a.download =
                        "content-analysis.json";

                    document.body.appendChild(
                        a
                    );

                    a.click();

                    a.remove();

                    URL.revokeObjectURL(
                        url
                    );

                } catch (error) {

                    console.error(
                        "Export failed:",
                        error
                    );

                    alert(
                        "Could not export analysis."
                    );
                }
            }
        );
    }


    /* =====================================================
       NEW ANALYSIS
    ====================================================== */

    const clearAll =
        document.getElementById(
            "clearAll"
        );

    if (clearAll) {

        clearAll.addEventListener(
            "click",
            event => {

                event.preventDefault();

                window.location.href = "/";
            }
        );
    }


    /* =====================================================
       SCORE BAR ANIMATION
    ====================================================== */

    document
        .querySelectorAll(
            ".score-fill, .dna-fill"
        )
        .forEach(element => {

            const width =
                element.style.width;

            element.style.width = "0%";

            setTimeout(
                () => {

                    element.style.width =
                        width;

                },
                100
            );
        });


    /* =====================================================
       INITIALIZE
    ====================================================== */

    renderFiles();
    updateButton();

});