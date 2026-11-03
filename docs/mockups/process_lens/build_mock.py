import sys
R = "/home/user/climate-risk"
page = open(f"{R}/dashboard/index.html").read()
mock = open(sys.argv[1]).read(); js = open(sys.argv[2]).read()
inj = f"<script>window.__MOCK={mock};</script>\n<script>{js}</script>\n</body>"
page = page.replace("<title>European Plant Heat Risk</title>", "<title>Process Limit Lens</title>").replace("</body>", inj, 1)
open(sys.argv[3], "w").write(page); print(len(page)/1e6, "MB")
