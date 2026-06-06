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

      document.getElementById(
        "success-modal"
      ).style.display = "flex";

      form.reset();

    } catch (err) {

      successMessage.innerText =
        "Something went wrong.";

      console.error(err);

    }

});

const closeModal =
document.getElementById("close-modal");

if(closeModal){

    closeModal.addEventListener("click", () => {

        document
        .getElementById("success-modal")
        .style.display = "none";

    });

}

const galleryImages =
document.querySelectorAll(
  ".gallery-grid img"
);

let touchStartX = 0;
let touchEndX = 0;

const lightbox =
document.getElementById(
  "lightbox"
);

const lightboxImage =
document.getElementById(
  "lightbox-image"
);

const closeLightbox =
document.getElementById(
  "close-lightbox"
);

const prevButton =
document.getElementById(
  "prev-image"
);

const nextButton =
document.getElementById(
  "next-image"
);

let currentIndex = 0;

galleryImages.forEach(
  (image,index) => {

    image.addEventListener(
      "click",
      () => {

        currentIndex = index;

        lightboxImage.src =
          image.src;

        lightbox.style.display =
          "flex";

      }
    );

});

function showImage(index){

    if(index < 0){

        index =
        galleryImages.length - 1;
    }

    if(index >= galleryImages.length){

        index = 0;
    }

    currentIndex = index;

    lightboxImage.src =
      galleryImages[
        currentIndex
      ].src;
}

prevButton.addEventListener(
    "click",
    showPreviousImage
);

nextButton.addEventListener(
    "click",
    showNextImage
);

closeLightbox.addEventListener(
  "click",
  () => {

    lightbox.style.display =
      "none";

});

lightbox.addEventListener(
  "click",
  (e) => {

    if(e.target === lightbox){

        lightbox.style.display =
          "none";

    }

});

lightbox.addEventListener(
    "touchstart",
    (e) => {

        touchStartX =
            e.changedTouches[0].screenX;

    },
    false
);

lightbox.addEventListener(
    "touchend",
    (e) => {

        touchEndX =
            e.changedTouches[0].screenX;

        handleSwipe();

    },
    false
);

const menuToggle =
document.getElementById(
  "menu-toggle"
);

const navLinks =
document.querySelector(
  ".nav-links"
);

menuToggle.addEventListener(
  "click",
  () => {

    navLinks.classList.toggle(
      "active"
    );

});

document
.querySelectorAll(
  ".nav-links a"
)
.forEach(link => {

    link.addEventListener(
      "click",
      () => {

        navLinks.classList.remove(
          "active"
        );

      }
    );

});

function showNextImage(){

    currentIndex =
        (currentIndex + 1)
        % galleryImages.length;

    lightboxImage.src =
        galleryImages[currentIndex].src;
}

function showPreviousImage(){

    currentIndex =
        (currentIndex - 1 + galleryImages.length)
        % galleryImages.length;

    lightboxImage.src =
        galleryImages[currentIndex].src;
}

function handleSwipe(){

    const swipeDistance =
        touchEndX - touchStartX;

    if(swipeDistance > 50){

        showPreviousImage();

    }

    if(swipeDistance < -50){

        showNextImage();

    }
}