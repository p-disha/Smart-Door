// WP-2
function submitPasscode(e) {
	console.log(document.getElementById("passcode-input").value);
	var apigClient2 = apigClientFactory.newClient();
	var params = {};
	
	var body = {
        'message': {
			'passcode-input':document.getElementById("passcode-input").value
		}
    }
	var additionalParams = {};
    apigClient2.passcodePost(params, body, additionalParams)
    .then(function(result){
        console.log(result);
	alert(result["data"]["body"]);
    }).catch( function(result){
        //This is where you would put an error callback
        console.log(result);
    });
}
