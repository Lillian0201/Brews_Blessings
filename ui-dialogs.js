(function () {
  "use strict";

  const CSS = `
.bb-dialog {
  width: min(380px, calc(100vw - 32px));
  max-width: none;
  padding: 22px;
  border: 1px solid #e3d2b8;
  border-radius: 12px;
  background: #fffaf1;
  color: #2a1b12;
  box-shadow: 0 12px 32px rgba(42, 27, 18, .2);
  font: 14px/1.45 system-ui, sans-serif;
}
.bb-dialog::backdrop { background: rgba(42, 27, 18, .45); }
.bb-dialog * { box-sizing: border-box; }
.bb-dialog h2 {
  margin: 0 0 16px;
  color: #2a1b12;
  font: bold 17px/1.3 Georgia, serif;
}
.bb-dialog-message {
  margin: -4px 0 16px;
  color: #6a5444;
  white-space: pre-wrap;
}
.bb-dialog-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 12px;
}
.bb-dialog-field label { color: #6a5444; font-size: 13px; }
.bb-dialog-field input,
.bb-dialog-field select {
  width: 100%;
  padding: 9px 10px;
  border: 1px solid #e3d2b8;
  border-radius: 8px;
  background: #fff;
  color: #2a1b12;
  font: inherit;
}
.bb-dialog-field input:focus,
.bb-dialog-field select:focus {
  outline: 2px solid #9a5c2c;
  outline-offset: 1px;
}
.bb-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
  margin-top: 20px;
}
.bb-dialog-button {
  border: 0;
  border-radius: 7px;
  padding: 9px 16px;
  cursor: pointer;
  font: inherit;
}
.bb-dialog-cancel { background: #efe2cf; color: #2a1b12; }
.bb-dialog-submit { background: #9a5c2c; color: #fff; font-weight: 700; }
.bb-dialog-submit:hover { background: #7d4a22; }
.bb-dialog-submit.bb-dialog-danger { background: #a63a2b; }
.bb-dialog-submit.bb-dialog-danger:hover { background: #842d22; }
.bb-dialog-button:focus-visible { outline: 2px solid #2a1b12; outline-offset: 2px; }
`;

  function injectCSS() {
    if (document.getElementById("bb-dialog-css")) return;
    const style = document.createElement("style");
    style.id = "bb-dialog-css";
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function open(title, fields, options) {
    return new Promise((resolve) => {
      injectCSS();

      const dialog = document.createElement("dialog");
      dialog.className = "bb-dialog";
      dialog.setAttribute("aria-labelledby", "bb-dialog-title");

      const form = document.createElement("form");
      form.noValidate = true;

      const heading = document.createElement("h2");
      heading.id = "bb-dialog-title";
      heading.textContent = title;
      form.appendChild(heading);

      if (options.message) {
        const message = document.createElement("p");
        message.className = "bb-dialog-message";
        message.textContent = options.message;
        form.appendChild(message);
      }

      const controls = {};
      fields.forEach((field) => {
        const wrapper = document.createElement("div");
        wrapper.className = "bb-dialog-field";

        const label = document.createElement("label");
        label.textContent = field.label;
        label.htmlFor = `bb-dialog-${field.key}`;
        wrapper.appendChild(label);

        let control;
        if (Array.isArray(field.options)) {
          control = document.createElement("select");
          field.options.forEach((option) => {
            const item = document.createElement("option");
            const value = typeof option === "string" ? option : option.value;
            item.value = value;
            item.textContent = typeof option === "string" ? option : option.label;
            control.appendChild(item);
          });
        } else {
          control = document.createElement("input");
          control.type = "text";
          if (field.inputMode) control.inputMode = field.inputMode;
          if (field.placeholder) control.placeholder = field.placeholder;
        }

        control.id = `bb-dialog-${field.key}`;
        control.name = field.key;
        if (field.required) control.required = true;
        if (field.initial !== undefined) control.value = String(field.initial);
        wrapper.appendChild(control);
        form.appendChild(wrapper);
        controls[field.key] = control;
      });

      const actions = document.createElement("div");
      actions.className = "bb-dialog-actions";
      if (options.showCancel !== false) {
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "bb-dialog-button bb-dialog-cancel";
        cancel.textContent = "Cancel";
        actions.appendChild(cancel);
        cancel.addEventListener("click", () => finish(options.cancelValue));
      }

      const submit = document.createElement("button");
      submit.type = "submit";
      submit.className = "bb-dialog-button bb-dialog-submit";
      if (options.danger) submit.classList.add("bb-dialog-danger");
      submit.textContent = options.okText || "OK";
      actions.appendChild(submit);
      form.appendChild(actions);
      dialog.appendChild(form);

      let settled = false;
      function finish(value) {
        if (settled) return;
        settled = true;
        dialog.close();
        dialog.remove();
        resolve(value);
      }

      form.addEventListener("submit", (event) => {
        event.preventDefault();
        finish(fields.reduce((values, field) => {
          values[field.key] = controls[field.key].value;
          return values;
        }, {}));
      });
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        finish(options.cancelValue);
      });

      document.body.appendChild(dialog);
      dialog.showModal();
      const firstControl = fields.length ? controls[fields[0].key] : submit;
      firstControl.focus();
    });
  }

  function ask(title, options) {
    const config = options || {};
    return open(title, [{
      key: "value",
      label: config.label || "",
      initial: config.initial,
      placeholder: config.placeholder
    }], { okText: config.okText || "OK", cancelValue: null }).then((result) =>
      result ? result.value : null);
  }

  function form(title, fields, options) {
    const config = options || {};
    return open(title, fields, {
      okText: config.okText || "OK",
      message: config.message,
      cancelValue: null
    });
  }

  function confirm(title, message, options) {
    const config = options || {};
    return open(title, [], {
      okText: config.okText || "OK",
      message,
      danger: config.danger,
      cancelValue: false
    });
  }

  function notify(title, message) {
    return open(title, [], {
      okText: "OK",
      message,
      showCancel: false,
      cancelValue: undefined
    });
  }

  window.BBDialog = { ask, form, confirm, notify };
})();
