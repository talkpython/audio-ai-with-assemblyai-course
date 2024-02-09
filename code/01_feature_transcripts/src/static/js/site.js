function onLoad() {
    var elements = document.getElementsByClassName('transcript-sentence');
    for (var i = 0; i < elements.length; i++) {
        var element = elements[i];
        element.addEventListener('click', playAtTime);
    }
}
function playAtTime(e) {
    var target = e.target;
    var player = document.getElementById('audio');
    var tx_time = target.getAttribute('data-time');
    console.log(tx_time);
    player.currentTime = tx_time;
    player.play();
    console.log('Trying to play at ' + tx_time);
    e.preventDefault();
    return false;
}
onLoad();
