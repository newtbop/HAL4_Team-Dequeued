let currentQuiz = [];
let currentQuestionIndex = 0;
let score = 0;
let recognition = null;
let quizActive = false;

async function uploadPDF() {
    const fileInput = document.getElementById("pdfFile");
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a PDF.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const loading = document.getElementById("loading");
    const quizControls = document.getElementById("quizControls");

    loading.classList.remove("hidden");
    quizControls.classList.add("hidden");

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        loading.classList.add("hidden");

        if (data.success) {

            currentQuiz = data.quiz || [];

            // Play summary audio
            const summaryAudio = new Audio(data.audio_url);
            summaryAudio.play();

            summaryAudio.onended = () => {
                speak("Summary complete. You may now start the quiz.");
                quizControls.classList.remove("hidden");
            };

        } else {
            alert(data.error);
        }

    } catch (err) {
        loading.classList.add("hidden");
        alert("Error occurred.");
    }
}

function speak(text, callback = null) {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;

    utterance.onend = () => {
        if (callback) callback();
    };

    speechSynthesis.speak(utterance);
}

function startVoiceQuiz() {
    if (!currentQuiz.length) {
        speak("Quiz not available.");
        return;
    }

    quizActive = true;
    currentQuestionIndex = 0;
    score = 0;

    askQuestion();
}

function stopQuiz() {
    quizActive = false;

    if (recognition) recognition.stop();
    speechSynthesis.cancel();

    document.getElementById("voiceStatus").innerText = "Quiz stopped.";
}

function askQuestion() {
    if (!quizActive) return;

    if (currentQuestionIndex >= currentQuiz.length) {
        speak(`Quiz complete. Your score is ${score} out of ${currentQuiz.length}.`);
        quizActive = false;
        return;
    }

    const q = currentQuiz[currentQuestionIndex];

    let text = `Question ${currentQuestionIndex + 1}. ${q.question}. `;

    q.options.forEach((opt, index) => {
        text += `Option ${String.fromCharCode(65 + index)}. ${opt}. `;
    });

    speak(text, () => {
        setTimeout(() => listenForAnswer(), 600);
    });
}

function listenForAnswer() {
    if (!quizActive) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        speak("Speech recognition is not supported.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.start();

    document.getElementById("voiceStatus").innerText = "Listening...";

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript.toLowerCase();
        evaluateAnswer(transcript);
    };
}

function evaluateAnswer(userSpeech) {
    if (!quizActive) return;

    const q = currentQuiz[currentQuestionIndex];
    let index = null;

    if (userSpeech.includes("a")) index = 0;
    else if (userSpeech.includes("b")) index = 1;
    else if (userSpeech.includes("c")) index = 2;
    else if (userSpeech.includes("d")) index = 3;

    if (index !== null && q.options[index] === q.answer) {
        score++;
        speak("Correct.");
    } else {
        speak("Incorrect.");
    }

    currentQuestionIndex++;

    setTimeout(() => askQuestion(), 1200);
}