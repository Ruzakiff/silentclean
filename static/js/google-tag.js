// Load Google Analytics tag
(function() {
    // Create script element
    const gtagScript = document.createElement('script');
    gtagScript.async = true;
    gtagScript.src = 'https://www.googletagmanager.com/gtag/js?id=G-3HLXDHRM3R';
    
    // Insert as first element in head
    const head = document.getElementsByTagName('head')[0];
    head.insertBefore(gtagScript, head.firstChild);
  
    // Initialize dataLayer and gtag function
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-3HLXDHRM3R');
  })();