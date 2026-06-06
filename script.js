const weddingDate =
new Date("2026-07-12T09:30:00");

function updateCountdown(){

    const now = new Date();

    const diff = weddingDate - now;

    const days =
    Math.floor(diff/(1000*60*60*24));

    const hours =
    Math.floor(
      (diff%(1000*60*60*24))
      /(1000*60*60)
    );

    const minutes =
    Math.floor(
      (diff%(1000*60*60))
      /(1000*60)
    );

    const seconds =
    Math.floor(
      (diff%(1000*60))
      /1000
    );

    document.getElementById("days")
      .textContent = days;

    document.getElementById("hours")
      .textContent = hours;

    document.getElementById("minutes")
      .textContent = minutes;

    document.getElementById("seconds")
      .textContent = seconds;
}

updateCountdown();

setInterval(updateCountdown,1000);

const music =
document.getElementById("music");

const toggle =
document.getElementById("music-toggle");

toggle.addEventListener("click", () => {

    if (music.paused) {

        music.play();

        toggle.innerText = "🔊";

    } else {

        music.pause();

        toggle.innerText = "🎵";

    }

});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {

    anchor.addEventListener("click", function(e) {

        e.preventDefault();

        document
            .querySelector(this.getAttribute("href"))
            .scrollIntoView({
                behavior: "smooth"
            });

    });

});

const form =
document.getElementById("rsvp-form");

const successMessage =
document.getElementById("success-message");

const scriptURL =
"https://script.google.com/macros/s/AKfycbyHRSyVMlwtaY8CIwmX1TDtv-9hAaDsYH0ZaTl0d_ZMGd48k2EGcgZglHjwVtZMKqFk/exec";

form.addEventListener(
  "submit",
  async (e) => {

    e.preventDefault();

    const wedding =
      document.getElementById(
        "wedding-attendance"
      ).checked;

    const reception =
      document.getElementById(
        "reception-attendance"
      ).checked;

    if (!wedding && !reception) {

      successMessage.innerText =
        "Please select Wedding, Reception, or both.";

      return;
    }

    const payload = {

      name:
        document.getElementById("name").value,

      phone:
        document.getElementById("phone").value,

      guests:
        document.getElementById("guests").value,

      wedding:
        wedding ? "Yes" : "No",

      reception:
        reception ? "Yes" : "No",

      message:
        document.getElementById("message").value

    };

    try {

      await fetch(scriptURL, {

        method: "POST",

        body:
          JSON.stringify(payload)

      });

      successMessage.innerText =
        "Thank you for your RSVP ❤️";

      form.reset();

    } catch (err) {

      successMessage.innerText =
        "Something went wrong.";

      console.error(err);

    }

});