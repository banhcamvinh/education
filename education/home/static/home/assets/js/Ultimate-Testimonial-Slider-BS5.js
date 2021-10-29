(function(document) {
	"use strict";
	const ready = (callback) => {
		if(document.readyState != "loading") callback();
		else document.addEventListener("DOMContentLoaded", callback);
	};
	ready(() => {
		const myCarousel = document.getElementById("carousel-t"),
			myCarouselInner = document.querySelector(".carousel-inner");
		if(myCarousel) {
			myCarouselInner.style.cssText = "height:" + myCarouselInner.clientHeight + "px; transition: height 0.5s ease-in-out;";
			myCarousel.addEventListener("slid.bs.carousel", (e) => {
				myCarouselInner.style.cssText = "height:" + e.relatedTarget.clientHeight + "px; transition: height 0.5s ease-in-out;";
			});
		}
	});
})(document); // End of use strict