async function getMedia(constraints) {
    let stream = null;
  
    try {
        stream = await navigator.mediaDevices.getUserMedia({video: false, audio:true});
        first_track = stream.getAudioTracks()[0]
        console.log(first_track)
        alert("access given! yay!")
      
        //   create a media recorder
        recorder = new MediaRecorder(stream)
        recorder.addEventListener('dataavailable', handleRecData)

        alert(recorder.state)
        alert("Starting Recording")
        recorder.start()
        alert(recorder.state)

        setTimeout(function(){
            recorder.stop()
            first_track.stop()
            alert("recording stopped")
        }
        , 5000)
        /* use the stream */
    } catch (err) {
        /* handle the error */
        alert("mic denied!")
        alert(err)
    }
  }

  function handleRecData(event){
    alert("it worked!!")
    console.log(event.data)
    const rec_sample = new Blob([event.data], {'type': 'audio/wav'})
    const sample_url = URL.createObjectURL(rec_sample)
    console.log(sample_url)
    const rec_audio = new Audio(sample_url)
    rec_audio.play()

    const send_req = new XMLHttpRequest()
    var save_form = new FormData()
    save_form.append("sample_data", rec_sample, "rec_sample")
    send_req.open("POST", "/process_sample", true)
    send_req.send(save_form)
    
  }

  