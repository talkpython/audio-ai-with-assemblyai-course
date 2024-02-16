function onLoad() {
    let elements = document.getElementsByClassName('transcript-sentence')

    for (let i = 0; i < elements.length; i++) {
        let element = elements[i];
        element.addEventListener('click', playAtTime);
    }
}

function playAtTime(e) {
    const target = e.target;
    const player = document.getElementById('audio') as HTMLAudioElement;

    let tx_time = target.getAttribute('data-time')
    console.log(tx_time)

    player.currentTime = tx_time;
    player.play();

    console.log('Trying to play at ' + tx_time)

    e.preventDefault();
    return false;
}

onLoad();
