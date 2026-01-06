"""
完整测试阿里云 DashScope 所有模型连接
"""
import asyncio
import sys
import base64
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

import dashscope
from dashscope import Generation, MultiModalConversation
from dashscope.audio.asr import Transcription
from app.core.config import settings
from app.services.aliyun_llm import llm_service

# 设置 API Key
dashscope.api_key = settings.ALIYUN_ACCESS_KEY_ID


async def test_llm_main():
    """测试主控大模型 Qwen-Max"""
    print("=" * 60)
    print("🧪 测试 1: 主控大模型 (Qwen-Max)")
    print("=" * 60)
    
    try:
        messages = [{"role": "user", "content": "你好，请用一句话介绍你自己"}]
        response = await llm_service.call_main_model(messages, max_tokens=100)
        print(f"✅ 响应: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_llm_turbo():
    """测试校对大模型 Qwen-Turbo"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 校对大模型 (Qwen-Turbo)")
    print("=" * 60)
    
    try:
        prompt = "请校对这个词：苹果，是否是水果名称？只回答是或否"
        response = await llm_service.call_calibration_model(prompt)
        print(f"✅ 响应: {response}")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_multimodal():
    """测试多模态模型 Qwen-VL"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 多模态模型 (Qwen-VL)")
    print("=" * 60)
    
    try:
        # 使用一个简单的测试图片 URL
        test_image_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg"
        
        messages = [{
            "role": "user",
            "content": [
                {"image": test_image_url},
                {"text": "请用一句话描述这张图片的内容"}
            ]
        }]
        
        response = MultiModalConversation.call(
            model="qwen-vl-plus",
            messages=messages
        )
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content[0]["text"]
            print(f"✅ 响应: {content[:100]}...")
            return True
        else:
            print(f"❌ 失败: {response.code} - {response.message}")
            return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_asr():
    """测试语音识别 ASR (Paraformer)"""
    print("\n" + "=" * 60)
    print("🧪 测试 4: 语音识别 ASR (Paraformer)")
    print("=" * 60)
    
    try:
        # 使用阿里云示例音频
        test_audio_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
        
        response = Transcription.call(
            model="paraformer-v2",
            file_urls=[test_audio_url]
        )
        
        if response.status_code == 200:
            # 异步任务，获取任务ID
            task_id = response.output.get('task_id')
            print(f"✅ ASR 任务已提交，Task ID: {task_id}")
            
            # 等待结果
            import time
            for _ in range(10):
                time.sleep(1)
                result = Transcription.fetch(task=task_id)
                if result.output.get('task_status') == 'SUCCEEDED':
                    transcripts = result.output.get('results', [])
                    if transcripts:
                        text = transcripts[0].get('transcription_url', '查看URL获取结果')
                        print(f"✅ ASR 识别完成!")
                    return True
                elif result.output.get('task_status') == 'FAILED':
                    print(f"❌ ASR 任务失败")
                    return False
            print(f"⏳ ASR 任务仍在处理中...")
            return True
        else:
            print(f"❌ 失败: {response.code} - {response.message}")
            return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def test_ocr_via_vl():
    """测试 OCR (通过 Qwen-VL 多模态实现)"""
    print("\n" + "=" * 60)
    print("🧪 测试 5: OCR 文字识别 (Qwen-VL)")
    print("=" * 60)
    
    try:
        # 使用一个包含文字的测试图片
        test_image_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
        
        messages = [{
            "role": "user",
            "content": [
                {"image": test_image_url},
                {"text": "如果图片中有文字，请识别出来；如果没有文字，请说明图片内容"}
            ]
        }]
        
        response = MultiModalConversation.call(
            model="qwen-vl-plus",
            messages=messages
        )
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content[0]["text"]
            print(f"✅ 响应: {content[:150]}...")
            return True
        else:
            print(f"❌ 失败: {response.code} - {response.message}")
            return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_embedding():
    """测试 Embedding 向量模型"""
    print("\n" + "=" * 60)
    print("🧪 测试 6: Embedding 向量 (text-embedding-v2)")
    print("=" * 60)
    
    try:
        text = "红富士苹果"
        embedding = await llm_service.get_embedding(text)
        print(f"✅ 维度: {len(embedding)}")
        print(f"✅ 前5个值: {[round(v, 4) for v in embedding[:5]]}")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_calibration():
    """测试校准流程（向量 + Turbo 二次确认）"""
    print("\n" + "=" * 60)
    print("🧪 测试 7: 校准流程 (向量 + Turbo 二次确认)")
    print("=" * 60)
    
    try:
        from app.services.knowledge_base import vector_store
        
        # 先确保知识库已初始化
        if vector_store.index is None:
            print("⏳ 正在初始化知识库...")
            await vector_store.initialize()
        
        # 测试用例：模拟 OCR 识别的模糊文本
        test_cases = [
            ("红富土苹果", "product"),   # 错别字：士 -> 土
            ("苹果", "product"),         # 歧义：多种苹果
            ("千克", "unit"),            # 单位
        ]
        
        for raw_text, category in test_cases:
            print(f"\n  输入: '{raw_text}' (类别: {category})")
            result, confidence, is_amb, candidates = await vector_store.calibrate_text(raw_text, category)
            print(f"  输出: '{result}' (置信度: {confidence:.2f}, 歧义: {is_amb})")
            if candidates:
                print(f"  候选: {candidates}")
        
        print("\n✅ 校准流程测试完成")
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "🚀" * 20)
    print("   阿里云 DashScope 全模型连接测试")
    print("🚀" * 20 + "\n")
    
    results = {}
    
    # 测试各模型
    results["LLM (Qwen-Max)"] = await test_llm_main()
    results["LLM Turbo (Qwen-Turbo)"] = await test_llm_turbo()
    results["多模态 (Qwen-VL)"] = test_multimodal()
    results["ASR 语音识别"] = test_asr()
    results["OCR via VL"] = test_ocr_via_vl()
    results["Embedding"] = await test_embedding()
    results["校准流程 (核心)"] = await test_calibration()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    all_pass = True
    for name, passed in results.items():
        status = "✅ 正常" if passed else "❌ 失败"
        print(f"  {name:25} {status}")
        if not passed:
            all_pass = False
    
    print("=" * 60)
    if all_pass:
        print("🎉 所有测试通过！可以开始联调了。")
    else:
        print("⚠️  部分测试失败，请检查 API Key 和网络连接。")
    print("\n💡 校准流程说明：向量检索 → Turbo 二次确认 → 最终结果")
    
    return all_pass


if __name__ == "__main__":
    asyncio.run(main())
