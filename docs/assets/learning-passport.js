(function () {
  "use strict";

  var STORAGE_KEY = "foundry-learning-passport-v1";
  var SCHEMA_VERSION = 1;
  var form = document.querySelector("[data-passport-form]");
  var status = document.querySelector("[data-save-status]");
  var decisionStatus = document.querySelector("[data-decision-status]");
  var fingerprintOutput = document.querySelector("[data-fingerprint-output]");
  var importInput = document.querySelector("[data-import-input]");
  var storageAvailable = true;
  var fingerprintFields = [
    "c4.instructionsHash",
    "c4.modelRoute",
    "c4.sourceSetHash",
    "c4.toolSetHash",
    "c4.policyHash",
    "c4.effectiveIdentity",
    "c4.parameters"
  ];

  if (!form) {
    return;
  }

  function fields() {
    return Array.from(form.elements).filter(function (element) {
      return element.name && !element.disabled && element.type !== "file";
    });
  }

  function setStatus(message, kind) {
    status.textContent = message;
    status.dataset.kind = kind || "info";
  }

  function readState() {
    var state = {};
    fields().forEach(function (element) {
      state[element.name] = element.type === "checkbox" ? element.checked : element.value;
    });
    return state;
  }

  function applyState(state) {
    fields().forEach(function (element) {
      if (!Object.prototype.hasOwnProperty.call(state, element.name)) {
        return;
      }
      if (element.type === "checkbox") {
        element.checked = state[element.name] === true;
      } else if (typeof state[element.name] === "string") {
        element.value = state[element.name];
      }
    });
    updateEvidence();
    updateFingerprint();
  }

  function save() {
    if (!storageAvailable) {
      setStatus("Local storage is unavailable. Continue working, then export before closing this page.", "warning");
      return;
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        schemaVersion: SCHEMA_VERSION,
        exportedAt: new Date().toISOString(),
        state: readState()
      }));
      setStatus("Saved locally in this browser. Export at every checkpoint.", "success");
    } catch (error) {
      storageAvailable = false;
      setStatus("Local storage failed. Your current entries remain usable; export them before closing this page.", "warning");
    }
  }

  function load() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        var payload = JSON.parse(saved);
        if (payload.schemaVersion === SCHEMA_VERSION && payload.state) {
          applyState(payload.state);
        }
      }
    } catch (error) {
      storageAvailable = false;
      setStatus("Local storage is unavailable. This page still works; use export to preserve your entries.", "warning");
    }
  }

  function stableConfiguration() {
    var state = readState();
    var configuration = {};
    fingerprintFields.forEach(function (name) {
      configuration[name] = (state[name] || "").trim();
    });
    return JSON.stringify(configuration);
  }

  function fallbackFingerprint(text) {
    var hash = 2166136261;
    for (var index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return "fnv1a-" + (hash >>> 0).toString(16).padStart(8, "0");
  }

  function updateFingerprint() {
    var normalized = stableConfiguration();
    var configurationComplete = fingerprintFields.every(function (name) {
      return normalizedValue(name).length > 0;
    });
    if (!configurationComplete) {
      fingerprintOutput.value = "";
      fingerprintOutput.placeholder = "Complete all seven configuration fields";
      updateEvidence();
      return;
    }
    fingerprintOutput.placeholder = "";
    if (window.crypto && window.crypto.subtle && window.TextEncoder) {
      window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(normalized)).then(function (buffer) {
        var value = Array.from(new Uint8Array(buffer)).map(function (byte) {
          return byte.toString(16).padStart(2, "0");
        }).join("");
        fingerprintOutput.value = "sha256-" + value;
        updateEvidence();
      }).catch(function () {
        fingerprintOutput.value = fallbackFingerprint(normalized);
        updateEvidence();
      });
    } else {
      fingerprintOutput.value = fallbackFingerprint(normalized);
      updateEvidence();
    }
  }

  function present(name) {
    var element = form.elements.namedItem(name);
    return element && String(element.value || "").trim().length > 0;
  }

  function integerValue(name) {
    var value = form.elements.namedItem(name).value;
    return /^\d+$/.test(value) ? Number(value) : null;
  }

  function setMeets(prefix, minimum, denominator) {
    var passes = integerValue("c5." + prefix + "Passes");
    var attempted = integerValue("c5." + prefix + "Attempted");
    var incomplete = integerValue("c5." + prefix + "Incomplete");
    var timedOut = integerValue("c5." + prefix + "TimedOut");
    var accessBlocked = integerValue("c5." + prefix + "AccessBlocked");
    return (
      passes !== null &&
      attempted === denominator &&
      passes >= minimum &&
      passes <= denominator &&
      incomplete === 0 &&
      timedOut === 0 &&
      accessBlocked === 0
    );
  }

  function normalizedValue(name) {
    return form.elements.namedItem(name).value.trim().toLowerCase();
  }

  function updateEvidence() {
    var requested = form.elements.namedItem("c5.ownDecision").value;
    var evidenceIdentityReady = [
      "c4.baselineEvaluationId",
      "c4.candidateEvaluationId",
      "c4.traceIds",
      "c5.developmentRunId",
      "c5.holdoutRunId",
    ].every(present) &&
      normalizedValue("c4.evidenceSubject") === "own-candidate" &&
      fingerprintFields.every(present) &&
      present("c4.candidateFingerprint");
    var behaviorGateReady =
      setMeets("development", 7, 8) &&
      setMeets("holdout", 3, 4) &&
      normalizedValue("c5.criticalResult") === "pass" &&
      ["none", "pass"].includes(normalizedValue("c5.regressionResult"));
    var operationalGateReady = normalizedValue("c5.operationalResult") === "pass";
    var authorizationGateReady = normalizedValue("c5.authorizationStatus") === "proven";
    var evidenceReady =
      evidenceIdentityReady &&
      behaviorGateReady &&
      operationalGateReady &&
      authorizationGateReady &&
      present("c5.authorizationEvidence");

    if (!requested) {
      decisionStatus.textContent = "No own-candidate decision recorded.";
      decisionStatus.dataset.outcome = "empty";
    } else if (requested === "release" && !evidenceReady) {
      decisionStatus.textContent = "Effective outcome: insufficient evidence. Use own-candidate evidence, complete its fingerprint, attempt all 8+4 cases with no incomplete, timed-out, or access-blocked cases, meet the 7/8 and 3/4 thresholds, and pass critical, regression, operational, and separate authorization gates.";
      decisionStatus.dataset.outcome = "insufficient";
    } else {
      decisionStatus.textContent = "Effective outcome: " + requested + ".";
      decisionStatus.dataset.outcome = requested.replaceAll(" ", "-");
    }
  }

  function exportPassport() {
    var payload = {
      schemaVersion: SCHEMA_VERSION,
      fixtureVersion: form.elements.namedItem("meta.fixtureVersion").value,
      exportedAt: new Date().toISOString(),
      state: readState()
    };
    var blob = new Blob([JSON.stringify(payload, null, 2)], {type: "application/json"});
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "learning-passport-" + (form.elements.namedItem("meta.seatLabel").value || "unassigned") + ".json";
    link.click();
    setTimeout(function () {
      URL.revokeObjectURL(link.href);
    }, 0);
    setStatus("Export created. Keep the JSON with your workshop evidence.", "success");
  }

  function importPassport(file) {
    var reader = new FileReader();
    reader.addEventListener("load", function () {
      try {
        var payload = JSON.parse(String(reader.result));
        if (
          payload.schemaVersion !== SCHEMA_VERSION ||
          !payload.state ||
          typeof payload.state !== "object" ||
          Array.isArray(payload.state)
        ) {
          throw new Error("Unsupported passport schema");
        }
        applyState(payload.state);
        save();
        setStatus("Import complete. Review the candidate fingerprint and evidence subject.", "success");
      } catch (error) {
        setStatus("Import failed: choose an unmodified learning passport JSON export.", "error");
      } finally {
        importInput.value = "";
      }
    });
    reader.addEventListener("error", function () {
      setStatus("Import failed: the selected file could not be read.", "error");
    });
    reader.readAsText(file);
  }

  function resetPassport() {
    if (!window.confirm("Reset every passport field in this browser? Export first if you need this evidence.")) {
      setStatus("Reset cancelled. Your evidence is unchanged.", "info");
      return;
    }
    form.reset();
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      storageAvailable = false;
    }
    updateFingerprint();
    updateEvidence();
    setStatus("Passport reset. No cloud resources or external data were changed.", "success");
  }

  form.addEventListener("input", function (event) {
    if (fingerprintFields.includes(event.target.name)) {
      updateFingerprint();
    }
    updateEvidence();
    save();
  });
  form.addEventListener("change", function () {
    updateEvidence();
    save();
  });

  document.querySelector("[data-export]").addEventListener("click", exportPassport);
  document.querySelector("[data-reset]").addEventListener("click", resetPassport);
  document.querySelector("[data-import-trigger]").addEventListener("click", function () {
    importInput.click();
  });
  importInput.addEventListener("change", function () {
    if (importInput.files && importInput.files[0]) {
      importPassport(importInput.files[0]);
    }
  });

  load();
  updateFingerprint();
  updateEvidence();
  if (storageAvailable) {
    setStatus("Ready. Entries stay in this browser until you reset them; export at every checkpoint.", "info");
  }
})();
