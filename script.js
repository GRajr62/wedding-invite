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