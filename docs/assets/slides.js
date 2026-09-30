/* Microsoft Foundry One-Day Workshop - slide presentation runtime. */

(function () {
  "use strict";

  var root = document.documentElement;
  var stage = document.querySelector(".deck-stage");
  var slides = stage ? Array.prototype.slice.call(stage.querySelectorAll(".slide")) : [];
  if (!stage || !slides.length) {
    return;
  }

  var STAGE_WIDTH = 1280;
  var STAGE_HEIGHT = 720;
  var FULLSCREEN_WAIT_MS = 1200;
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var current = 0;
  var revealed = 0;
  var changingFromHistory = false;

  function fragments(slide) {
    return Array.prototype.slice.call(slide.querySelectorAll(".fragment"));
  }

  function slideLabel(slide) {
    var heading = slide.querySelector("h1, h2");
    return heading ? heading.textContent.trim() : slide.id;
  }

  slides.forEach(function (slide, index) {
    if (!slide.id) {
      slide.id = "slide-" + (index + 1);
    }
    slide.tabIndex = -1;
    slide.setAttribute("role", "group");
    slide.setAttribute("aria-roledescription", "slide");
    slide.setAttribute(
      "aria-label",
      index + 1 + " of " + slides.length + ": " + slideLabel(slide)
    );
  });

  function buildChrome() {
    var controls = document.createElement("div");
    controls.className = "deck-controls";
    controls.setAttribute("role", "group");
    controls.setAttribute("aria-label", "Presentation controls");
    controls.innerHTML =
      '<button class="button" type="button" data-slide-action="previous">Previous</button>' +
      '<button class="button" type="button" data-slide-action="next">Next</button>' +
      '<button class="button" type="button" data-slide-action="fullscreen">Full screen</button>' +
      '<button class="button" type="button" data-theme-toggle>Theme</button>';

    var progress = document.createElement("div");
    progress.className = "deck-progress";
    progress.setAttribute("aria-live", "polite");

    var progressbar = document.createElement("div");
    progressbar.className = "deck-progressbar";
    progressbar.setAttribute("role", "progressbar");
    progressbar.setAttribute("aria-label", "Slide progress");
    progressbar.tabIndex = -1;
    progressbar.innerHTML = "<span></span>";

    var status = document.createElement("div");
    status.className = "deck-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    var orientation = document.createElement("p");
    orientation.className = "deck-orientation";
    orientation.textContent = "Rotate your device for a larger presentation view.";

    document.body.appendChild(controls);
    document.body.appendChild(progress);
    document.body.appendChild(progressbar);
    document.body.appendChild(status);
    document.body.appendChild(orientation);
    document.dispatchEvent(new CustomEvent("workshop:controls-ready"));

    controls.addEventListener("click", function (event) {
      var button = event.target.closest("[data-slide-action]");
      if (!button) {
        return;
      }
      var action = button.getAttribute("data-slide-action");
      if (action === "previous") {
        back();
      } else if (action === "next") {
        forward();
      } else {
        toggleFullscreen();
      }
    });
  }

  function scaleStage() {
    var scale = Math.min(window.innerWidth / STAGE_WIDTH, window.innerHeight / STAGE_HEIGHT);
    stage.style.setProperty("--deck-scale", String(scale));
  }

  function setFragmentState(slide) {
    fragments(slide).forEach(function (fragment, index) {
      var visible = reducedMotion.matches || index < revealed;
      fragment.toggleAttribute("data-visible", visible);
      fragment.setAttribute("aria-hidden", visible ? "false" : "true");
    });
  }

  function updateUrl(mode) {
    var url = new URL(window.location.href);
    url.hash = slides[current].id;
    if (mode === "push") {
      window.history.pushState({ slide: slides[current].id }, "", url);
    } else if (mode === "replace") {
      window.history.replaceState({ slide: slides[current].id }, "", url);
    }
  }

  function render(historyMode, focusSlide) {
    slides.forEach(function (slide, index) {
      slide.toggleAttribute("data-current", index === current);
      slide.setAttribute("aria-hidden", index === current ? "false" : "true");
    });

    setFragmentState(slides[current]);

    var progress = document.querySelector(".deck-progress");
    var progressbar = document.querySelector(".deck-progressbar");
    var percent = ((current + 1) / slides.length) * 100;
    progress.textContent = current + 1 + " / " + slides.length;
    progressbar.setAttribute("aria-valuemin", "1");
    progressbar.setAttribute("aria-valuemax", String(slides.length));
    progressbar.setAttribute("aria-valuenow", String(current + 1));
    progressbar.setAttribute(
      "aria-valuetext",
      current + 1 + " of " + slides.length + ": " + slideLabel(slides[current])
    );
    progressbar.style.setProperty("--deck-progress", percent + "%");

    if (historyMode) {
      updateUrl(historyMode);
    }
    if (focusSlide) {
      progressbar.focus({ preventScroll: true });
    }
  }

  function goTo(index, showAll, historyMode) {
    var next = Math.max(0, Math.min(slides.length - 1, index));
    var changed = next !== current;
    current = next;
    revealed = showAll && !reducedMotion.matches ? fragments(slides[current]).length : 0;
    render(changed ? historyMode : null, changed);
  }

  function forward() {
    var points = fragments(slides[current]);
    if (!reducedMotion.matches && revealed < points.length) {
      revealed += 1;
      render(null, false);
    } else {
      goTo(current + 1, false, "push");
    }
  }

  function back() {
    if (!reducedMotion.matches && revealed > 0) {
      revealed -= 1;
      render(null, false);
    } else {
      goTo(current - 1, true, "push");
    }
  }

  function wholeSlide(offset) {
    goTo(current + offset, offset < 0, "push");
  }

  function setFullscreenStatus(message, state) {
    document.querySelector(".deck-status").textContent = message;
    root.setAttribute("data-fullscreen-state", state);
  }

  function waitForFullscreen(expected) {
    return new Promise(function (resolve) {
      if (Boolean(document.fullscreenElement) === expected) {
        resolve(true);
        return;
      }

      var settled = false;
      var finish = function (value) {
        if (settled) {
          return;
        }
        settled = true;
        document.removeEventListener("fullscreenchange", changed);
        window.clearTimeout(timer);
        resolve(value);
      };
      var changed = function () {
        finish(Boolean(document.fullscreenElement) === expected);
      };
      var timer = window.setTimeout(function () {
        finish(Boolean(document.fullscreenElement) === expected);
      }, FULLSCREEN_WAIT_MS);
      document.addEventListener("fullscreenchange", changed);
    });
  }

  function toggleFullscreen() {
    var entering = !document.fullscreenElement;
    var operation;
    setFullscreenStatus("", "pending");
    if (!entering) {
      operation = document.exitFullscreen();
    } else if (root.requestFullscreen) {
      operation = root.requestFullscreen();
    } else {
      operation = Promise.reject(new Error("Fullscreen API unavailable"));
    }

    Promise.resolve(operation)
      .then(function () {
        return waitForFullscreen(entering);
      })
      .then(function (changed) {
        if (!changed) {
          setFullscreenStatus(
            "Full screen did not start. Use the browser presentation controls.",
            "unavailable"
          );
        } else {
          setFullscreenStatus("", entering ? "active" : "inactive");
        }
      })
      .catch(function () {
        setFullscreenStatus(
          "Full screen is unavailable in this browser. Use the browser presentation controls.",
          "unavailable"
        );
      });
  }

  function isInteractive(target) {
    return Boolean(
      target.closest(
        "a, button, input, select, textarea, summary, [contenteditable], [role='button']"
      )
    );
  }

  document.addEventListener("keydown", function (event) {
    if (
      event.altKey ||
      event.ctrlKey ||
      event.metaKey ||
      isInteractive(event.target)
    ) {
      return;
    }

    if (event.key === "ArrowRight" || event.key === "ArrowDown" || event.key === " ") {
      event.preventDefault();
      forward();
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      back();
    } else if (event.key === "PageDown") {
      event.preventDefault();
      wholeSlide(1);
    } else if (event.key === "PageUp") {
      event.preventDefault();
      wholeSlide(-1);
    } else if (event.key === "Home") {
      event.preventDefault();
      goTo(0, false, "push");
    } else if (event.key === "End") {
      event.preventDefault();
      goTo(slides.length - 1, true, "push");
    } else if (event.key === "f" || event.key === "F") {
      event.preventDefault();
      toggleFullscreen();
    }
  });

  document.addEventListener("click", function (event) {
    if (!isInteractive(event.target)) {
      forward();
    }
  });

  var touchStartX = null;
  var touchStartY = null;
  document.addEventListener(
    "touchstart",
    function (event) {
      if (isInteractive(event.target) || event.changedTouches.length !== 1) {
        touchStartX = null;
        return;
      }
      touchStartX = event.changedTouches[0].clientX;
      touchStartY = event.changedTouches[0].clientY;
    },
    { passive: true }
  );
  document.addEventListener(
    "touchend",
    function (event) {
      if (touchStartX === null || event.changedTouches.length !== 1) {
        return;
      }
      var deltaX = event.changedTouches[0].clientX - touchStartX;
      var deltaY = event.changedTouches[0].clientY - touchStartY;
      touchStartX = null;
      touchStartY = null;
      if (Math.abs(deltaX) < 45 || Math.abs(deltaX) <= Math.abs(deltaY)) {
        return;
      }
      if (deltaX < 0) {
        forward();
      } else {
        back();
      }
    },
    { passive: true }
  );

  function restoreFromHash() {
    var wanted = slides.findIndex(function (slide) {
      return "#" + slide.id === window.location.hash;
    });
    if (wanted >= 0) {
      current = wanted;
      revealed = 0;
      render(null, true);
    }
  }

  window.addEventListener("popstate", function () {
    changingFromHistory = true;
    restoreFromHash();
    changingFromHistory = false;
  });
  window.addEventListener("hashchange", function () {
    if (!changingFromHistory) {
      restoreFromHash();
    }
  });
  window.addEventListener("resize", scaleStage);
  document.addEventListener("fullscreenchange", function () {
    root.setAttribute(
      "data-fullscreen-state",
      document.fullscreenElement ? "active" : "inactive"
    );
  });
  reducedMotion.addEventListener("change", function () {
    render(null, false);
  });

  root.setAttribute("data-presentation", "true");
  buildChrome();
  scaleStage();

  var initial = slides.findIndex(function (slide) {
    return "#" + slide.id === window.location.hash;
  });
  current = initial >= 0 ? initial : 0;
  render("replace", false);
  root.setAttribute("data-slides-ready", "true");
})();
