const weddingDate =
new Date("2026-07-12T09:30:00");

function updateCountdown(){

    const now = new Date();

    const diff =
    weddingDate - now;

    const days =
    Math.floor(diff/(1000*60*60*24));

    document.getElementById("days")
        .innerText = days;
}

setInterval(updateCountdown,1000);