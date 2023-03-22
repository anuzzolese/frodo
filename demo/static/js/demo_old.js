
$(document).ready(function(){
	$("#btn-opts").click(showOpts);
	$("#btn-examples").click(showExamples);
	$(".btn-use").click(useExample);
	$(".btn-read").click(submit)
});

function showOpts(){
    hideExamples();
	$("#options").show();
	$("#btn-opts").html("Hide options");
	$("#btn-opts").unbind("click");
	$("#btn-opts").click(hideOpts);
}

function hideOpts(){
	$("#options").hide();
	$("#btn-opts").html("Show options");
	$("#btn-opts").unbind("click");
	$("#btn-opts").click(showOpts);
}

function showExamples(){
	hideOpts();
	$("#examples").show();
	$("#btn-examples").html("Hide examples");
	$("#btn-examples").unbind("click");
	$("#btn-examples").click(hideExamples);
}

function hideExamples(){
	$("#examples").hide();
	$("#btn-examples").html("Show examples");
	$("#btn-examples").unbind("click");
	$("#btn-examples").click(showExamples);
}

function useExample(){
	var example = $(".example", $(this).parent()).html();
	$("#text").html(example);
}

function submit(){

	var endpoint = jQuery(".btn-read").attr("endpoint");
	jQuery(this).parent().append('<div class="loading"><img src="' + jQuery('base').attr('href') + '/static/img/giphy.gif"/></div>');
    
    data = {
	    text: jQuery("#text").val()
    }
    
    jQuery.ajax({
        url: endpoint,
  		data: data,
  		dataType: "text"  		
  	}).done(function(data){
		jQuery(".loading").remove();
		var blob = new Blob([data], { type: "text/turtle" });
		
		//Check the Browser type and download the File.
        var isIE = false || !!document.documentMode;
        if (isIE) {
            window.navigator.msSaveBlob(blob, fileName);
        } else {
            var url = window.URL || window.webkitURL;
            link = url.createObjectURL(blob);
            var a = $("<a />");
            a.attr("download", fileName);
            a.attr("href", link);
            $("body").append(a);
            a[0].click();
            $("body").remove(a);
        }
	});
}