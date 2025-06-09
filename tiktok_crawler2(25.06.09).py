# pip install playwright pandas openpyxl
# python -m playwright install chromium

# 실행 시: python tiktok_crawler2.py

import asyncio
import re
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

async def crawl_tiktok_channel(channel_url, target_video_count=None):
    video_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False → 눈으로 확인 가능
        context = await browser.new_context()
        page = await context.new_page()

        async def handle_response(response):
            url = response.url
            if "/api/post/item_list/" in url:
                print(f"[DEBUG] Found item_list API: {url}")
                try:
                    data = await response.json()
                    for item in data.get("itemList", []):
                        video_id = item.get("id")
                        desc = item.get("desc", "")
                        stats = item.get("stats", {})
                        play_count = stats.get("playCount", 0)
                        like_count = stats.get("diggCount", 0)
                        comment_count = stats.get("commentCount", 0)
                        share_count = stats.get("shareCount", 0)

                        video_url = f"https://www.tiktok.com/@{account_name}/video/{video_id}"

                        # 중복 방지
                        if video_url not in [v["영상 URL"] for v in video_links]:
                            video_links.append({
                                "계정명": account_name,
                                "영상 URL": video_url,
                                "제목": desc,
                                "조회수": play_count,
                                "좋아요": like_count,
                                "댓글": comment_count,
                                "공유": share_count
                            })

                        print(f"[DEBUG] 현재까지 영상 개수: {len(video_links)}")

                        # ⭐ 목표 개수 도달 시 바로 종료
                        if target_video_count and len(video_links) >= target_video_count:
                            print(f"[INFO] 목표 영상 {target_video_count}개 도달! 스크롤 중단 예정.")
                            asyncio.create_task(page.close())  # 페이지 먼저 종료
                            asyncio.create_task(browser.close())  # 브라우저 종료
                            return

                except Exception as e:
                    print(f"[ERROR] Failed to parse item_list response: {e}")

        # 이벤트 리스너 등록
        page.on("response", handle_response)

        # 페이지 열기
        print(f"[INFO] 채널 페이지 오픈 중: {channel_url}")
        await page.goto(channel_url)
        await asyncio.sleep(3)

        # 스크롤 자동 수행
        scroll_pause_time = 2
        max_scrolls = 20  # 원하는 만큼 늘려도 됨
        for i in range(max_scrolls):
            if target_video_count and len(video_links) >= target_video_count:
                break

            print(f"[INFO] 스크롤 중... ({i+1})")
            await page.mouse.wheel(0, 5000)
            await asyncio.sleep(scroll_pause_time)

        print("[INFO] Done scrolling. Waiting for final responses...")
        await asyncio.sleep(5)

        await browser.close()

    return video_links

if __name__ == "__main__":
    # 사용할 TikTok 채널 URL
    channel_url = "https://www.tiktok.com/@diggle"

    # 계정명 추출
    account_name = channel_url.split("@")[1].split("?")[0]
    print(f"[INFO] 계정명: {account_name}")

    # ⭐ 원하는 영상 개수 설정 (None이면 전체 가져오기)
    target_video_count = 15  # 예: 15개만 가져오기 / None → 전체 다 가져오기

    # 크롤링 실행
    print(f"[INFO] TikTok 크롤링 시작: {account_name} (목표: {target_video_count if target_video_count else '전체'})")
    video_links = asyncio.run(crawl_tiktok_channel(channel_url, target_video_count=target_video_count))

    # 결과 DataFrame 저장
    df = pd.DataFrame(video_links)
    print(df)

    # 날짜 기반 파일명 생성
    output_filename = f"{account_name}_videos_{datetime.now().strftime('%Y%m%d')}.xlsx"
    df.to_excel(output_filename, index=False)
    print(f"[INFO] 엑셀 저장 완료: {output_filename}")
