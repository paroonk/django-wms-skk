$(document).ready(function () {
    // Refresh Log
    function refresh_log() {
        $(".refresh").load(location.href + " .refresh > *")
    }
    setInterval(refresh_log, 1000)
})
