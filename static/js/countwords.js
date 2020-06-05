var count = document.getElementById('count');
var nlg = document.getElementById('nlg');
var globalWordCounter = 0;
var WORD_LIMIT = 10;

nlg.addEventListener('keydown', function(e) {
  if (globalWordCounter > WORD_LIMIT && e.code !== "Backspace") {
    e.preventDefault();
    return alert("You have reached the word limit");
  }
});

nlg.addEventListener('keyup', function(e) {
  wordCounter(e.target.value);
});

function isWord(str) {
  var alphaNumericFound = false;
  for (var i = 0; i < str.length; i++) {
    var code = str.charCodeAt(i);
    if ((code > 47 && code < 58) || // numeric (0-9)
        (code > 64 && code < 91) || // upper alpha (A-Z)
        (code > 96 && code < 123)) { // lower alpha (a-z)
      alphaNumericFound = true;
      return alphaNumericFound;
    }
  }
  return alphaNumericFound;
}

function wordCounter(text) {
  var text = nlg.value.split(' ');
  var wordCount = 0;
  for (var i = 0; i < text.length; i++) {
    if (!text[i] == ' ' && isWord(text[i])) {
      wordCount++;
    }
  }
  globalWordCounter = wordCount;
  count.innerText = wordCount;
}
