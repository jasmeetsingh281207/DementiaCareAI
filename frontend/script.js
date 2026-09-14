/* =========================================================
   DEMENTIACARE
   FRONTEND INTERACTION SYSTEM
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  /* =====================================================
       ELEMENTS
    ===================================================== */

  const voiceButton = document.getElementById("voiceButton");

  const heroSpeakButton = document.getElementById("heroSpeakButton");

  const listenWelcome = document.getElementById("listenWelcome");

  const voiceStatus = document.getElementById("voiceStatus");

  const liveStatus = document.getElementById("liveStatus");

  const companionMessage = document.getElementById("companionMessage");

  const voiceWave = document.getElementById("voiceWave");

  const chatForm = document.getElementById("chatForm");

  const messageInput = document.getElementById("messageInput");

  const sendButton = document.getElementById("sendButton");

  const conversationArea = document.getElementById("conversationArea");

  const languageButton = document.getElementById("languageButton");

  const languageLabel = document.getElementById("languageLabel");

  const voiceLanguage = document.getElementById("voiceLanguage");

  const settingsButton = document.getElementById("settingsButton");

  const caregiverButton = document.getElementById("caregiverButton");

  const largeTextToggle = document.getElementById("largeTextToggle");

  const contrastToggle = document.getElementById("contrastToggle");

  const spokenToggle = document.getElementById("spokenToggle");

  const greeting = document.getElementById("greeting");

  /* =====================================================
       STATE
    ===================================================== */

  let selectedLanguage = "English";

  let speechLanguage = "en-IN";

  let spokenResponses = true;

  let isListening = false;

  let recognition = null;

  /* =====================================================
       GREETING
    ===================================================== */

  function updateGreeting() {
    const hour = new Date().getHours();

    if (hour < 12) {
      greeting.textContent = "Good morning";
    } else if (hour < 17) {
      greeting.textContent = "Good afternoon";
    } else {
      greeting.textContent = "Good evening";
    }
  }

  updateGreeting();

  /* =====================================================
       MODAL SYSTEM
    ===================================================== */

  function openModal(id) {
    const modal = document.getElementById(id);

    if (!modal) return;

    modal.classList.add("open");

    modal.setAttribute("aria-hidden", "false");
  }

  function closeModal(id) {
    const modal = document.getElementById(id);

    if (!modal) return;

    modal.classList.remove("open");

    modal.setAttribute("aria-hidden", "true");
  }

  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => {
      closeModal(button.dataset.close);
    });
  });

  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        overlay.classList.remove("open");
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      document.querySelectorAll(".modal-overlay.open").forEach((modal) => {
        modal.classList.remove("open");
      });
    }
  });

  /* =====================================================
       HEADER BUTTONS
    ===================================================== */

  languageButton.addEventListener("click", () => {
    openModal("languageModal");
  });

  settingsButton.addEventListener("click", () => {
    openModal("settingsModal");
  });

  caregiverButton.addEventListener("click", () => {
    openModal("caregiverModal");
  });

  /* =====================================================
       LANGUAGE
    ===================================================== */

  document.querySelectorAll(".language-option").forEach((option) => {
    option.addEventListener("click", () => {
      document.querySelectorAll(".language-option").forEach((item) => {
        item.classList.remove("active");
      });

      option.classList.add("active");

      selectedLanguage = option.dataset.language;

      speechLanguage = option.dataset.code;

      languageLabel.textContent = selectedLanguage;

      voiceLanguage.textContent = selectedLanguage;

      closeModal("languageModal");

      updateCompanionLanguage();
    });
  });

  function updateCompanionLanguage() {
    const messages = {
      English: "Good morning. How are you feeling today?",

      हिन्दी: "नमस्ते। आज आप कैसा महसूस कर रहे हैं?",

      ਪੰਜਾਬੀ: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ। ਅੱਜ ਤੁਸੀਂ ਕਿਵੇਂ ਮਹਿਸੂਸ ਕਰ ਰਹੇ ਹੋ?",

      বাংলা: "নমস্কার। আজ আপনি কেমন অনুভব করছেন?",
    };

    companionMessage.textContent =
      messages[selectedLanguage] || messages["English"];
  }

  /* =====================================================
       SETTINGS
    ===================================================== */

  function setupToggle(button, callback) {
    button.addEventListener("click", () => {
      const active = button.classList.toggle("active");

      button.setAttribute("aria-pressed", active);

      callback(active);
    });
  }

  setupToggle(largeTextToggle, (active) => {
    document.body.classList.toggle("large-text", active);

    localStorage.setItem("largeText", active);
  });

  setupToggle(contrastToggle, (active) => {
    document.body.classList.toggle("high-contrast", active);

    localStorage.setItem("highContrast", active);
  });

  setupToggle(spokenToggle, (active) => {
    spokenResponses = active;

    localStorage.setItem("spokenResponses", active);
  });

  /* =====================================================
       LOAD SETTINGS
    ===================================================== */

  const savedLargeText = localStorage.getItem("largeText") === "true";

  const savedContrast = localStorage.getItem("highContrast") === "true";

  const savedSpoken = localStorage.getItem("spokenResponses");

  if (savedLargeText) {
    document.body.classList.add("large-text");

    largeTextToggle.classList.add("active");

    largeTextToggle.setAttribute("aria-pressed", "true");
  }

  if (savedContrast) {
    document.body.classList.add("high-contrast");

    contrastToggle.classList.add("active");

    contrastToggle.setAttribute("aria-pressed", "true");
  }

  if (savedSpoken !== null) {
    spokenResponses = savedSpoken === "true";

    spokenToggle.classList.toggle("active", spokenResponses);

    spokenToggle.setAttribute("aria-pressed", spokenResponses);
  }

  /* =====================================================
       TEXT TO SPEECH
    ===================================================== */

  function speakText(text) {
    if (!spokenResponses || !("speechSynthesis" in window)) {
      return;
    }

    window.speechSynthesis.cancel();

    const speech = new SpeechSynthesisUtterance(text);

    speech.lang = speechLanguage;

    speech.rate = 0.9;

    speech.pitch = 1;

    speech.onstart = () => {
      setLiveStatus("Speaking");

      voiceWave.classList.add("active");
    };

    speech.onend = () => {
      setLiveStatus("Ready");

      voiceWave.classList.remove("active");
    };

    window.speechSynthesis.speak(speech);
  }

  /* =====================================================
       WELCOME VOICE
    ===================================================== */

  listenWelcome.addEventListener("click", () => {
    speakText(companionMessage.textContent);
  });

  /* =====================================================
       SPEECH RECOGNITION
    ===================================================== */

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();

    recognition.continuous = false;

    recognition.interimResults = true;

    recognition.lang = speechLanguage;

    recognition.onstart = () => {
      isListening = true;

      voiceButton.classList.add("listening");

      voiceWave.classList.add("active");

      voiceStatus.textContent = "I'm listening...";

      setLiveStatus("Listening");
    };

    recognition.onresult = (event) => {
      let transcript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }

      messageInput.value = transcript.trim();

      autoResize();
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);

      isListening = false;

      resetVoiceUI();

      voiceStatus.textContent = "I couldn't hear that. Try again.";
    };

    recognition.onend = () => {
      isListening = false;

      resetVoiceUI();

      const message = messageInput.value.trim();

      if (message) {
        sendMessage(message);
      }
    };
  }

  function startListening() {
    if (!recognition) {
      voiceStatus.textContent = "Voice input is not supported in this browser.";

      return;
    }

    if (isListening) {
      recognition.stop();

      return;
    }

    recognition.lang = speechLanguage;

    recognition.start();
  }

  function resetVoiceUI() {
    voiceButton.classList.remove("listening");

    voiceWave.classList.remove("active");

    voiceStatus.textContent = "Tap to speak";

    setLiveStatus("Ready");
  }

  voiceButton.addEventListener("click", startListening);

  heroSpeakButton.addEventListener("click", () => {
    document.getElementById("voiceSection").scrollIntoView({
      behavior: "smooth",
      block: "center",
    });

    setTimeout(startListening, 500);
  });

  /* =====================================================
       VOICE STATUS
    ===================================================== */

  function setLiveStatus(text) {
    liveStatus.innerHTML = `<span></span>${text}`;
  }

  /* =====================================================
       CHAT
    ===================================================== */

  chatForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!message) return;

    sendMessage(message);
  });

  async function sendMessage(message) {
    addMessage(message, "user");

    messageInput.value = "";

    autoResize();

    showTyping();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          message: message,
        }),
      });

      if (!response.ok) {
        throw new Error("Server returned an error.");
      }

      const data = await response.json();

      removeTyping();

      const reply =
        data.response || data.message || "I'm here with you. Please try again.";

      addMessage(reply, "ai");

      companionMessage.textContent = reply;

      speakText(reply);
    } catch (error) {
      console.error(error);

      removeTyping();

      const fallback =
        "I'm here with you. I couldn't connect right now, but you can try again.";

      addMessage(fallback, "ai");

      companionMessage.textContent = fallback;
    }
  }

  /* =====================================================
       ADD CHAT MESSAGE
    ===================================================== */

  function addMessage(text, sender) {
    const wrapper = document.createElement("div");

    wrapper.className = `chat-message ${sender}-message`;

    if (sender === "ai") {
      wrapper.innerHTML = `

                <div class="chat-avatar">
                    D
                </div>

                <div class="chat-bubble">

                    <span>
                        DEMENTIACARE
                    </span>

                    <p></p>

                </div>

            `;
    } else {
      wrapper.innerHTML = `

                <div class="chat-bubble">

                    <span>
                        YOU
                    </span>

                    <p></p>

                </div>

            `;
    }

    wrapper.querySelector("p").textContent = text;

    conversationArea.appendChild(wrapper);

    conversationArea.scrollTop = conversationArea.scrollHeight;
  }

  /* =====================================================
       TYPING INDICATOR
    ===================================================== */

  function showTyping() {
    removeTyping();

    const typing = document.createElement("div");

    typing.id = "typingIndicator";

    typing.className = "chat-message ai-message";

    typing.innerHTML = `

            <div class="chat-avatar">
                D
            </div>

            <div class="chat-bubble">

                <span>
                    DEMENTIACARE
                </span>

                <p>
                    Thinking...
                </p>

            </div>

        `;

    conversationArea.appendChild(typing);

    conversationArea.scrollTop = conversationArea.scrollHeight;
  }

  function removeTyping() {
    const typing = document.getElementById("typingIndicator");

    if (typing) {
      typing.remove();
    }
  }

  /* =====================================================
       TEXTAREA AUTO RESIZE
    ===================================================== */

  function autoResize() {
    messageInput.style.height = "auto";

    messageInput.style.height = Math.min(messageInput.scrollHeight, 130) + "px";
  }

  messageInput.addEventListener("input", autoResize);

  /* =====================================================
       ENTER TO SEND
    ===================================================== */

  messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      chatForm.requestSubmit();
    }
  });

  /* =====================================================
       ACTIVITY CARDS
    ===================================================== */

  document.querySelectorAll(".activity-card").forEach((card) => {
    card.addEventListener("click", () => {
      const heading = card.querySelector("h3")?.textContent.trim();

      if (!heading) return;

      const prompts = {
        Talk: "Let's have a friendly conversation. How are you feeling today?",

        Memories: "Let's look at some familiar memories together.",

        Music: "Let's listen to something familiar together.",

        Activities: "Let's do a short activity together.",
      };

      const message =
        prompts[heading] || `Let's start ${heading.toLowerCase()}.`;

      companionMessage.textContent = message;

      speakText(message);
    });
  });

  /* =====================================================
       ROUTINE ITEMS
    ===================================================== */

  document.querySelectorAll(".routine-item").forEach((item) => {
    item.addEventListener("click", () => {
      const title = item.querySelector(".routine-info strong")?.textContent;

      if (!title) return;

      const message = `Let's take a look at ${title.toLowerCase()}.`;

      companionMessage.textContent = message;

      speakText(message);
    });
  });

  /* =====================================================
       FULL ROUTINE
    ===================================================== */

  document.getElementById("routineButton").addEventListener("click", () => {
    const routineSection = document.querySelector(".routine-section");

    routineSection.scrollIntoView({
      behavior: "smooth",
    });
  });

  /* =====================================================
       INITIAL STATUS
    ===================================================== */

  setLiveStatus("Ready");
});
