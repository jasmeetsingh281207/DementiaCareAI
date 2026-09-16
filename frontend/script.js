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

  // null means no patient language has been explicitly selected.  The server
  // can then use its existing local language detection.
  let selectedLanguage = null;

  const languageLocales = {
    en: "en-IN",
    hi: "hi-IN",
    hinglish: "hi-IN",
    as: "as-IN",
    bn: "bn-IN",
    mr: "mr-IN",
    ur: "ur-IN",
    pa: "pa-IN",
    gu: "gu-IN",
    or: "or-IN",
    ta: "ta-IN",
    te: "te-IN",
    kn: "kn-IN",
    ml: "ml-IN",
    ne: "ne-NP",
    mni: "mni-IN",
    brx: "brx-IN",
    kha: "kha-IN",
    grt: "grt-IN",
    lus: "lus-IN",
    trp: "trp-IN",
  };

  let speechLanguage = languageLocales.en;

  const sessionId =
    localStorage.getItem("dementiaCareSession") ||
    (window.crypto && typeof window.crypto.randomUUID === "function"
      ? window.crypto.randomUUID()
      : String(Date.now()));

  localStorage.setItem("dementiaCareSession", sessionId);

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
        overlay.setAttribute("aria-hidden", "true");
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      document.querySelectorAll(".modal-overlay.open").forEach((modal) => {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
      });
    }
  });

  /* =====================================================
       HEADER BUTTONS
    ===================================================== */

  if (languageButton) {
    languageButton.addEventListener("click", () => {
      openModal("languageModal");
    });
  }

  if (settingsButton) {
    settingsButton.addEventListener("click", () => {
      openModal("settingsModal");
    });
  }

  if (caregiverButton) {
    caregiverButton.addEventListener("click", () => {
      openModal("caregiverModal");
      loadCaregiverData();
    });
  }

  const caregiverRetryButton = document.getElementById("caregiverRetryButton");

  if (caregiverRetryButton) {
    caregiverRetryButton.addEventListener("click", loadCaregiverData);
  }

  /* =====================================================
       CAREGIVER DASHBOARD
    ===================================================== */

  function setCaregiverLoading(isLoading) {
    const loading = document.getElementById("caregiverLoading");
    const content = document.getElementById("caregiverContent");
    const error = document.getElementById("caregiverError");

    if (loading) {
      loading.hidden = !isLoading;
    }

    if (isLoading) {
      if (content) {
        content.hidden = true;
      }

      if (error) {
        error.hidden = true;
      }
    }
  }

  function setCaregiverError(message) {
    const loading = document.getElementById("caregiverLoading");
    const content = document.getElementById("caregiverContent");
    const error = document.getElementById("caregiverError");
    const errorText = document.getElementById("caregiverErrorText");

    if (loading) {
      loading.hidden = true;
    }

    if (content) {
      content.hidden = true;
    }

    if (error) {
      error.hidden = false;
    }

    if (errorText) {
      errorText.textContent = message || "Please try again in a moment.";
    }
  }

  function setCaregiverContentVisible() {
    const loading = document.getElementById("caregiverLoading");
    const content = document.getElementById("caregiverContent");
    const error = document.getElementById("caregiverError");

    if (loading) {
      loading.hidden = true;
    }

    if (error) {
      error.hidden = true;
    }

    if (content) {
      content.hidden = false;
    }
  }

  function formatReminderTime(value) {
    if (!value) {
      return "Time not specified";
    }

    const text = String(value).trim();

    /*
      Supports:
      2026-09-16 15:00
      2026-09-16T15:00
      15:00
    */

    const match = text.match(/(?:^|\s|T)(\d{1,2}):(\d{2})(?:\s*$)/);

    if (!match) {
      return text;
    }

    const hour = Number(match[1]);
    const minute = match[2];

    const suffix = hour >= 12 ? "PM" : "AM";

    return `${hour % 12 || 12}:${minute} ${suffix}`;
  }

  function formatReminderStatus(status) {
    const normalized = String(status || "scheduled").replace(/_/g, " ");

    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }

  function renderCaregiverReminders(reminders) {
    const list = document.getElementById("caregiverReminderList");

    const summary = document.getElementById("caregiverReminderSummary");

    if (!list) {
      return;
    }

    const items = Array.isArray(reminders) ? reminders : [];

    /*
      Do not depend on the browser's local date here.

      The backend may be using a different timezone from the
      browser. Showing the reminders returned by the backend
      makes the caregiver panel reliable for the demo.
    */

    const visibleItems = items.filter((reminder) => {
      const status = String(reminder?.status || "").toLowerCase();

      return status !== "cancelled" && status !== "completed";
    });

    if (summary) {
      summary.textContent =
        visibleItems.length === 1
          ? "1 reminder"
          : `${visibleItems.length} reminders`;
    }

    if (!visibleItems.length) {
      list.innerHTML =
        '<div class="caregiver-empty">No active reminders found.</div>';

      return;
    }

    list.innerHTML = "";

    visibleItems.forEach((reminder) => {
      const item = document.createElement("div");

      item.className = "caregiver-reminder";

      const main = document.createElement("div");

      main.className = "caregiver-reminder-main";

      const message = document.createElement("div");

      message.className = "caregiver-reminder-message";

      message.textContent = reminder.message || "Reminder";

      const time = document.createElement("div");

      time.className = "caregiver-reminder-time";

      time.textContent = formatReminderTime(reminder.time);

      const status = document.createElement("div");

      status.className = "caregiver-reminder-status";

      status.textContent = formatReminderStatus(reminder.status);

      main.appendChild(message);

      main.appendChild(time);

      item.appendChild(main);

      item.appendChild(status);

      list.appendChild(item);
    });
  }

  function renderCaregiverOverview(data) {
    const activity = data.activity || {};

    const reminders = data.reminders || {};

    const memory = data.memory || {};

    const conversation = data.conversation || {};

    const cognitive = data.cognitive || {};

    const companion = data.companion || {};

    const today = data.today || {};

    const todayActivity = today.activity || {};

    const todayReminders = today.reminders || {};

    const todayConversation = today.conversation || {};

    const activityCompleted = Number(
      todayActivity.completed ?? activity.today_completed ?? 0,
    );

    const activityTotal = Number(
      todayActivity.total ?? activity.today_total ?? 0,
    );

    const reminderTotal = Number(
      todayReminders.total ?? reminders.today_total ?? 0,
    );

    const reminderCompleted = Number(
      todayReminders.completed ?? reminders.today_completed ?? 0,
    );

    const reminderPending = Number(reminders.pending ?? 0);

    const reminderInProgress = Number(reminders.in_progress ?? 0);

    const memoryTotal = Number(memory.total_memories ?? 0);

    const mediaItems = Number(memory.media_items ?? 0);

    const userMessages = Number(
      todayConversation.user_messages ?? conversation.today_user_messages ?? 0,
    );

    const assistantMessages = Number(
      todayConversation.assistant_messages ??
        conversation.today_assistant_messages ??
        0,
    );

    const conversationMessages = Number(
      todayConversation.messages ?? conversation.today_messages ?? 0,
    );

    const averageScore = Number(cognitive.average_score);

    const latestScore = Number(cognitive.latest_score);

    const activitiesValue = document.getElementById("caregiverActivitiesValue");

    const activitiesDetail = document.getElementById(
      "caregiverActivitiesDetail",
    );

    const remindersValue = document.getElementById("caregiverRemindersValue");

    const remindersDetail = document.getElementById("caregiverRemindersDetail");

    const memoryValue = document.getElementById("caregiverMemoryValue");

    const memoryDetail = document.getElementById("caregiverMemoryDetail");

    const companionValue = document.getElementById("caregiverCompanionValue");

    const companionDetail = document.getElementById("caregiverCompanionDetail");

    const cognitiveValue = document.getElementById("caregiverCognitiveValue");

    const cognitiveDetail = document.getElementById("caregiverCognitiveDetail");

    const conversationValue = document.getElementById(
      "caregiverConversationValue",
    );

    const conversationDetail = document.getElementById(
      "caregiverConversationDetail",
    );

    if (activitiesValue) {
      activitiesValue.textContent = `${activityCompleted} / ${activityTotal}`;
    }

    if (activitiesDetail) {
      activitiesDetail.textContent =
        activityTotal === 0
          ? "no activities recorded today"
          : `${activityCompleted} completed today`;
    }

    if (remindersValue) {
      remindersValue.textContent = String(reminderTotal);
    }

    if (remindersDetail) {
      remindersDetail.textContent =
        `${reminderCompleted} completed · ` +
        `${reminderPending} pending · ` +
        `${reminderInProgress} in progress`;
    }

    if (memoryValue) {
      memoryValue.textContent = String(memoryTotal);
    }

    if (memoryDetail) {
      memoryDetail.textContent =
        `${mediaItems} media item` + `${mediaItems === 1 ? "" : "s"} stored`;
    }

    if (companionValue) {
      companionValue.textContent =
        companion.conversation_active === false ? "Inactive" : "Active";
    }

    if (companionDetail) {
      companionDetail.textContent =
        `${userMessages} user · ` +
        `${assistantMessages} assistant messages today`;
    }

    if (cognitiveValue) {
      cognitiveValue.textContent = Number.isFinite(averageScore)
        ? `${Math.round(averageScore * 100)}%`
        : "—";
    }

    if (cognitiveDetail) {
      cognitiveDetail.textContent = Number.isFinite(latestScore)
        ? `latest score ${Math.round(latestScore * 100)}%`
        : "average score";
    }

    if (conversationValue) {
      conversationValue.textContent = String(conversationMessages);
    }

    if (conversationDetail) {
      conversationDetail.textContent = "messages today";
    }
  }

  async function fetchJson(url) {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    let data;

    try {
      data = await response.json();
    } catch (error) {
      throw new Error(`Invalid response from ${url}`);
    }

    if (!response.ok || data?.success === false) {
      throw new Error(data?.error || `Request failed (${response.status})`);
    }

    return data;
  }

  async function loadCaregiverData() {
    setCaregiverLoading(true);

    try {
      const [overview, reminderData] = await Promise.all([
        fetchJson("/api/caregiver/overview"),
        fetchJson("/api/reminders"),
      ]);

      renderCaregiverOverview(overview);

      renderCaregiverReminders(reminderData.reminders || []);

      setCaregiverContentVisible();
    } catch (error) {
      console.error("Caregiver data unavailable:", error);

      setCaregiverError(
        "The caregiver dashboard could not retrieve the latest information. Please try again.",
      );
    }
  }

  /* =====================================================
       LANGUAGE
    ===================================================== */

  document.querySelectorAll(".language-option").forEach((option) => {
    option.addEventListener("click", () => {
      document.querySelectorAll(".language-option").forEach((item) => {
        item.classList.remove("active");
      });

      option.classList.add("active");

      // Use the canonical API code from the selected language pill (hi, bn,
      // pa, ta, etc.), never its human-readable label.
      selectedLanguage = option.dataset.code || null;

      speechLanguage = languageLocales[selectedLanguage] || "en-IN";

      if (languageLabel) {
        languageLabel.textContent = option.dataset.language;
      }

      if (voiceLanguage) {
        voiceLanguage.textContent = option.dataset.language;
      }

      closeModal("languageModal");

      updateCompanionLanguage();
    });
  });

  function updateCompanionLanguage() {
    const messages = {
      en: "Hello, I'm Mitra. How are you feeling today?",

      hi: "नमस्ते। आज आप कैसा महसूस कर रहे हैं?",

      hinglish: "Namaste. Aaj aap kaisa feel kar rahe hain?",

      as: "নমস্কাৰ। আজি আপুনি কেনে অনুভৱ কৰিছে?",

      bn: "নমস্কার। আজ আপনি কেমন অনুভব করছেন?",

      mr: "नमस्कार। आज तुम्हाला कसे वाटत आहे?",

      ur: "السلام علیکم۔ آج آپ کیسا محسوس کر رہے ہیں؟",

      pa: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ। ਅੱਜ ਤੁਸੀਂ ਕਿਵੇਂ ਮਹਿਸੂਸ ਕਰ ਰਹੇ ਹੋ?",

      gu: "નમસ્તે. આજે તમને કેવું લાગે છે?",

      or: "ନମସ୍କାର। ଆଜି ଆପଣ କେମିତି ଅନୁଭବ କରୁଛନ୍ତି?",

      ta: "வணக்கம். இன்று நீங்கள் எப்படி உணர்கிறீர்கள்?",

      te: "నమస్కారం. ఈ రోజు మీరు ఎలా అనుభవిస్తున్నారు?",

      kn: "ನಮಸ್ಕಾರ. ಇಂದು ನಿಮಗೆ ಹೇಗನಿಸುತ್ತಿದೆ?",

      ml: "നമസ്കാരം. ഇന്ന് നിങ്ങൾക്ക് എങ്ങനെ തോന്നുന്നു?",

      ne: "नमस्ते। आज तपाईंलाई कस्तो महसुस भइरहेको छ?",

      mni: "ꯍꯥꯏꯔꯤꯕꯥ। ꯅꯪꯅ ꯂꯩꯕꯥ ꯀꯔꯤꯅꯣ?",

      brx: "नमस्कार। दिनै नोंथांनो माबोरै महरै?",

      kha: "Khublei. Kumno phi sngew mynta?",

      grt: "On'na. Nara nara agana?",

      lus: "Chibai. Vawiin i rilru chu eng nge?",

      trp: "Khulumkha. Nwngni angni?",
    };

    if (companionMessage) {
      companionMessage.textContent = messages[selectedLanguage] || messages.en;
    }
  }

  /* =====================================================
       SETTINGS
    ===================================================== */

  function setupToggle(button, callback) {
    if (!button) return;

    button.addEventListener("click", () => {
      const active = button.classList.toggle("active");

      button.setAttribute("aria-pressed", String(active));

      callback(active);
    });
  }

  setupToggle(largeTextToggle, (active) => {
    document.body.classList.toggle("large-text", active);

    localStorage.setItem("largeText", String(active));
  });

  setupToggle(contrastToggle, (active) => {
    document.body.classList.toggle("high-contrast", active);

    localStorage.setItem("highContrast", String(active));
  });

  setupToggle(spokenToggle, (active) => {
    spokenResponses = active;

    localStorage.setItem("spokenResponses", String(active));
  });

  /* =====================================================
       LOAD SETTINGS
    ===================================================== */

  const savedLargeText = localStorage.getItem("largeText") === "true";

  const savedContrast = localStorage.getItem("highContrast") === "true";

  const savedSpoken = localStorage.getItem("spokenResponses");

  if (savedLargeText && largeTextToggle) {
    document.body.classList.add("large-text");

    largeTextToggle.classList.add("active");

    largeTextToggle.setAttribute("aria-pressed", "true");
  }

  if (savedContrast && contrastToggle) {
    document.body.classList.add("high-contrast");

    contrastToggle.classList.add("active");

    contrastToggle.setAttribute("aria-pressed", "true");
  }

  if (savedSpoken !== null && spokenToggle) {
    spokenResponses = savedSpoken === "true";

    spokenToggle.classList.toggle("active", spokenResponses);

    spokenToggle.setAttribute("aria-pressed", String(spokenResponses));
  }

  /* =====================================================
       TEXT TO SPEECH
    ===================================================== */

  function speakText(text) {
    if (!spokenResponses || !("speechSynthesis" in window)) {
      return;
    }

    if (!text || !String(text).trim()) {
      return;
    }

    window.speechSynthesis.cancel();

    const speech = new SpeechSynthesisUtterance(String(text));

    speech.lang = speechLanguage;

    speech.rate = 0.9;

    speech.pitch = 1;

    speech.onstart = () => {
      setLiveStatus("Speaking");

      if (voiceWave) {
        voiceWave.classList.add("active");
      }
    };

    speech.onend = () => {
      setLiveStatus("Ready");

      if (voiceWave) {
        voiceWave.classList.remove("active");
      }
    };

    speech.onerror = () => {
      setLiveStatus("Ready");

      if (voiceWave) {
        voiceWave.classList.remove("active");
      }
    };

    window.speechSynthesis.speak(speech);
  }

  /* =====================================================
       WELCOME VOICE
    ===================================================== */

  if (listenWelcome) {
    listenWelcome.addEventListener("click", () => {
      speakText(companionMessage ? companionMessage.textContent : "");
    });
  }

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

      if (voiceButton) {
        voiceButton.classList.add("listening");
      }

      if (voiceWave) {
        voiceWave.classList.add("active");
      }

      if (voiceStatus) {
        voiceStatus.textContent = "I'm listening...";
      }

      setLiveStatus("Listening");
    };

    recognition.onresult = (event) => {
      let transcript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }

      if (messageInput) {
        messageInput.value = transcript.trim();

        autoResize();
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);

      isListening = false;

      resetVoiceUI();

      if (voiceStatus) {
        voiceStatus.textContent = "I couldn't hear that. Try again.";
      }
    };

    recognition.onend = () => {
      isListening = false;

      resetVoiceUI();

      if (messageInput && messageInput.value.trim() && voiceStatus) {
        voiceStatus.textContent =
          "Voice captured. Press Send when you are ready.";
      }
    };
  }

  function startListening() {
    if (!recognition) {
      if (voiceStatus) {
        voiceStatus.textContent =
          "Voice input is not supported in this browser.";
      }

      return;
    }

    if (isListening) {
      recognition.stop();

      return;
    }

    recognition.lang = speechLanguage;

    try {
      recognition.start();
    } catch (error) {
      console.warn("Speech recognition could not start:", error);
    }
  }

  function resetVoiceUI() {
    if (voiceButton) {
      voiceButton.classList.remove("listening");
    }

    if (voiceWave) {
      voiceWave.classList.remove("active");
    }

    if (voiceStatus) {
      voiceStatus.textContent = "Tap to speak";
    }

    setLiveStatus("Ready");
  }

  if (voiceButton) {
    voiceButton.addEventListener("click", startListening);
  }

  if (heroSpeakButton) {
    heroSpeakButton.addEventListener("click", () => {
      const voiceSection = document.getElementById("voiceSection");

      if (voiceSection) {
        voiceSection.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }

      setTimeout(startListening, 500);
    });
  }

  /* =====================================================
       VOICE STATUS
    ===================================================== */

  function setLiveStatus(text) {
    if (!liveStatus) {
      return;
    }

    liveStatus.innerHTML = `<span></span>${text}`;
  }

  /* =====================================================
       CHAT
    ===================================================== */

  if (chatForm) {
    chatForm.addEventListener("submit", (event) => {
      event.preventDefault();

      if (!messageInput) {
        return;
      }

      const message = messageInput.value.trim();

      if (!message) {
        return;
      }

      sendMessage(message);
    });
  }

  async function sendMessage(message) {
    addMessage(message, "user");

    if (messageInput) {
      messageInput.value = "";

      autoResize();
    }

    showTyping();

    if (sendButton) {
      sendButton.disabled = true;
    }

    try {
      const response = await fetch("/api/chat", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          message: message,
          // An explicit UI choice is authoritative; omitting language keeps
          // the backend's existing local-detection behaviour intact.
          ...(selectedLanguage ? { language: selectedLanguage } : {}),
          session_id: sessionId,
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

      if (companionMessage) {
        companionMessage.textContent = reply;
      }

      speechLanguage =
        (data.language_info && data.language_info.speech_locale) ||
        languageLocales[data.language] ||
        speechLanguage;

      speakText(reply);
    } catch (error) {
      console.error("Chat error:", error);

      removeTyping();

      const fallback =
        "I'm here with you. I couldn't connect right now, but you can try again.";

      addMessage(fallback, "ai");

      if (companionMessage) {
        companionMessage.textContent = fallback;
      }
    } finally {
      if (sendButton) {
        sendButton.disabled = false;
      }
    }
  }

  /* =====================================================
       ADD CHAT MESSAGE
    ===================================================== */

  function addMessage(text, sender) {
    if (!conversationArea) {
      return;
    }

    const wrapper = document.createElement("div");

    wrapper.className = `chat-message ${sender}-message`;

    if (sender === "ai") {
      wrapper.innerHTML = `
        <div class="chat-avatar">
          M
        </div>

        <div class="chat-bubble">
          <span>
            MITRA
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

    const paragraph = wrapper.querySelector("p");

    if (paragraph) {
      paragraph.textContent = text;
    }

    conversationArea.appendChild(wrapper);

    conversationArea.scrollTop = conversationArea.scrollHeight;
  }

  /* =====================================================
       TYPING INDICATOR
    ===================================================== */

  function showTyping() {
    if (!conversationArea) {
      return;
    }

    removeTyping();

    const typing = document.createElement("div");

    typing.id = "typingIndicator";

    typing.className = "chat-message ai-message";

    typing.innerHTML = `
      <div class="chat-avatar">
        M
      </div>

      <div class="chat-bubble">
        <span>
          MITRA
        </span>

        <p>
          Mitra is thinking...
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
    if (!messageInput) {
      return;
    }

    messageInput.style.height = "auto";

    messageInput.style.height = Math.min(messageInput.scrollHeight, 130) + "px";
  }

  if (messageInput) {
    messageInput.addEventListener("input", autoResize);
  }

  /* =====================================================
       ENTER TO SEND
    ===================================================== */

  if (messageInput) {
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();

        if (typeof chatForm.requestSubmit === "function") {
          chatForm.requestSubmit();
        } else {
          chatForm.dispatchEvent(
            new Event("submit", {
              bubbles: true,
              cancelable: true,
            }),
          );
        }
      }
    });
  }

  /* =====================================================
       ACTIVITY CARDS
    ===================================================== */

  document.querySelectorAll(".activity-card").forEach((card) => {
    card.addEventListener("click", () => {
      const heading = card.querySelector("h3")?.textContent.trim();

      if (!heading) {
        return;
      }

      const prompts = {
        Talk: "Let's have a friendly conversation. How are you feeling today?",

        Memories: "Let's look at some familiar memories together.",

        Music: "Let's listen to something familiar together.",

        Activities: "Let's do a short activity together.",
      };

      const message =
        prompts[heading] || `Let's start ${heading.toLowerCase()}.`;

      if (companionMessage) {
        companionMessage.textContent = message;
      }

      speakText(message);
    });
  });

  /* =====================================================
       ROUTINE ITEMS
    ===================================================== */

  document.querySelectorAll(".routine-item").forEach((item) => {
    item.addEventListener("click", () => {
      const title = item
        .querySelector(".routine-info strong")
        ?.textContent.trim();

      if (!title) {
        return;
      }

      const message = `Let's take a look at ${title.toLowerCase()}.`;

      if (companionMessage) {
        companionMessage.textContent = message;
      }

      speakText(message);
    });
  });

  /* =====================================================
       FULL ROUTINE
    ===================================================== */

  const routineButton = document.getElementById("routineButton");

  if (routineButton) {
    routineButton.addEventListener("click", () => {
      const routineSection = document.querySelector(".routine-section");

      if (routineSection) {
        routineSection.scrollIntoView({
          behavior: "smooth",
        });
      }
    });
  }

  /* =====================================================
       INITIAL STATUS
    ===================================================== */

  setLiveStatus("Ready");
});
