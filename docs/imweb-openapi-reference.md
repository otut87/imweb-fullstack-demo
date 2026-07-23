Title: Reference

URL Source: https://developers-docs.imweb.me/reference

Markdown Content:
v1.0

OpenAPI 3.1.0

# Imweb OpenAPI

[LLM용 문서 보기](https://r.jina.ai/https://developers-docs.imweb.me/reference)

Server 

Server:https://openapi.imweb.me

## Authentication

Selected Auth Type: access-token

OAuth2.0 Access Token
Bearer Token  : 

Show Password

Client Libraries

Shell Ruby Node.js PHP Python

More Select from all clients

Shell Curl

## OAuth2.0

​Copy link

OAuth2.0

OAuth2.0 Operations

*   [get/oauth2/authorize](https://developers-docs.imweb.me/reference)
*   [post/oauth2/token](https://developers-docs.imweb.me/reference)

### 인가 코드 발급

​Copy link

Query Parameters

*   response Type Copy link to responseType  Type: string required Example code   OAuth 2.0 인증 요청 타입을 지정합니다.

"code": 권한 부여 코드 흐름(Authorization Code Flow)을 사용하여 액세스 토큰을 발급받기 위한 인증 코드를 요청합니다.

현재 서비스에서는 Authorization Code Flow만 지원하므로 "code"로 값이 고정됩니다.    
*   client Id Copy link to clientId  Type: string required Example 9fdb5b45-b4cb-4bae-a1bd-12bad9098744   아임웹으로부터 발급 받은 클라이언트 앱 ID    
*   redirect Uri Copy link to redirectUri  Type: string required Example https://example.com/callback   인증 코드를 전달 받을 URI, 앱 등록 시 등록한 redirectUri 값

HTTPS 사용을 권장합니다.    
*   
scope Copy link to scope  Type: string required Example member-info:read product:write order:write   

접근이 필요한 권한을 공백으로 구분하여 전달

    *   site-info:read: 사이트 정보 읽기
    *   site-info:write: 사이트 정보 읽기∙쓰기
    *   member-info:read: 회원 정보 읽기
    *   member-info:write: 회원 정보 읽기∙쓰기
    *   promotion:read: 프로모션 읽기
    *   promotion:write: 프로모션 읽기∙쓰기
    *   community:read: 커뮤니티 읽기
    *   community:write: 커뮤니티 읽기∙쓰기
    *   product:read: 상품 읽기
    *   product:write: 상품 읽기∙쓰기
    *   order:read: 주문 읽기
    *   order:write: 주문 읽기∙쓰기
    *   payment:read: 결제 읽기
    *   payment:write: 결제 읽기∙쓰기
    *   script:read: 스크립트 읽기
    *   script:write: 스크립트 읽기∙쓰기
    *   statistics:read: 통계 읽기
    *   statistics:write: 통계 읽기∙쓰기

*   state Copy link to state  Type: string required Example f47ac10b-58cc-4372-a567-0e02b2c3d479   CSRF 공격 방지를 위한 임의의 문자열    
*   site Code Copy link to siteCode  Type: string required Example S2025012450f7813d2ddau   사이트 코드    

Responses

*   302  인가 코드 발급 성공 시 요청한 redirect uri로 인가 코드 전달   application/json  
*   default  ## Error List Up

| statusCode | errorCode | message |
| --- | --- | --- |
| 500 | 10000 | 아임웹 내부 서버에서 에러가 발생했습니다. |
| 400 | 10001 | 잘못된 입력으로 요청하였습니다. |
| 400 | 10003 | 잘못된 데이터로 요청하였습니다. |
| 400 | 10004 | 잘못된 입력으로 요청하였습니다. |
| 400 | 30098 | 클라이언트 정보가 올바르지 않습니다. |
| 400 | 30098 | 클라이언트 정보가 올바르지 않습니다. |
| 400 | 30099 | 요청한 scope가 올바르지 않습니다. |
| 400 | 30099 | 요청한 scope가 올바르지 않습니다. |
| 401 | 30101 | 토큰이 유효하지 않습니다. |
| 401 | 30102 | 토큰이 만료되었습니다. |
| 403 | 30103 | 권한이 부족합니다. |
| 400 | 30104 | 유닛 코드가 유효하지 않습니다. |
| 401 | 30105 | 인증 정보가 유효하지 않습니다. |  

Request Example for get/oauth2/authorize

Shell Curl 

```curl
curl 'https://openapi.imweb.me/oauth2/authorize?responseType=code&clientId=9fdb5b45-b4cb-4bae-a1bd-12bad9098744&redirectUri=https%3A%2F%2Fexample.com%2Fcallback&scope=member-info%3Aread%20product%3Awrite%20order%3Awrite&state=f47ac10b-58cc-4372-a567-0e02b2c3d479&siteCode=S2025012450f7813d2ddau'
```

Copy

Copy

Test Request(get /oauth2/authorize)

Status: 302 Status: default

```json
https://example.com/callback?code=8d6aea1a2cdf55a9c212c34e0c974fa494927b7898384d801c8b3518a92526f2
```

Copy

Copy

인가 코드 발급 성공 시 요청한 redirect uri로 인가 코드 전달

### Access Token 발급 요청 & 재발급 요청

​Copy link

Auth Required

Body

required

x-www-form-urlencoded

*   
One of TokenRequestDto   

Access Token 발급 요청  

    *   client Id Copy link to clientId  Type: string required  아임웹으로부터 발급 받은 클라이언트 앱 ID  
    *   client Secret Copy link to clientSecret  Type: string required  아임웹으로부터 발급 받은 클라이언트 앱 Secret  
    *   code Copy link to code  Type: string required  authorization code  
    *   grant Type Copy link to grantType  Type: string required Example grantType=authorization_code   grantType authorization_code  
    *   redirect Uri Copy link to redirectUri  Type: string required  액세스 토큰을 전달 받을 URI, 앱 등록 시 등록한 redirectUri 값  

Responses

*   200  토큰 발급 성공   application/json  
*   default  ## Error List Up

| statusCode | errorCode | message |
| --- | --- | --- |
| 500 | 10000 | 아임웹 내부 서버에서 에러가 발생했습니다. |
| 400 | 10001 | 잘못된 입력으로 요청하였습니다. |
| 400 | 10003 | 잘못된 데이터로 요청하였습니다. |
| 400 | 10004 | 잘못된 입력으로 요청하였습니다. |
| 400 | 30098 | 클라이언트 정보가 올바르지 않습니다. |
| 400 | 30099 | 요청한 scope가 올바르지 않습니다. |
| 400 | 30100 | 인증 코드가 유효하지 않습니다. |
| 401 | 30101 | 토큰이 유효하지 않습니다. |
| 401 | 30102 | 토큰이 만료되었습니다. |
| 403 | 30103 | 권한이 부족합니다. |
| 400 | 30104 | 유닛 코드가 유효하지 않습니다. |
| 401 | 30105 | 인증 정보가 유효하지 않습니다. |
| 400 | 30122 | 요청은 application/x-www-form-urlencoded 형식으로 전송되어야 합니다. |
| 400 | 30123 | 잘못된 redirect uri입니다. |
| 400 | 30124 | 잘못된 인증 코드입니다. |
| 400 | 30125 | 만료된 인증 코드입니다. |  

Request Example for post/oauth2/token

Shell Curl 

```curl
curl https://openapi.imweb.me/oauth2/token \
  --request POST \
  --header 'Content-Type: x-www-form-urlencoded' \
  --header 'Authorization: Basic username:password' \
  --data '{
  "clientId": "",
  "clientSecret": "",
  "redirectUri": "",
  "code": "",
  "grantType": "grantType=authorization_code"
}'
```

cURL Copy

cURL Copy

Test Request(post /oauth2/token)

Status: 200 Status: default

Show Schema - [x]  

```json
{
  "statusCode": 200,
  "data": {
    "accessToken": "string",
    "refreshToken": "string",
    "scope": "string"
  }
}
```

JSON Copy

JSON Copy

토큰 발급 성공

Search...Ask AI

*    Introduction 
*    OAuth2.0 Close Group  
    *       인가 코드 발급 HTTP Method: GET
    *       Access Token 발급 요청 & 재발급 요청 HTTP Method: POST

*    Site-Info Open Group  
*    Member-Info Open Group  
*    Community Open Group  
*    Promotion Open Group  
*    Product Open Group  
*    Order Open Group  
*    Script Open Group  
*    Payment Open Group  
*    Models Open Group  

Sidebar Menu[![Image 1: logo](https://api.scalar.com/cdn/images/jkVGph6gp-qOjh9bodqh1/ky8GEGEGs3dQ1UNI8ZzK_.png)![Image 2: logo](https://api.scalar.com/cdn/images/jkVGph6gp-qOjh9bodqh1/VsK-2LEN_Licq4cjhfVbh.png)](https://developers-docs.imweb.me/)

[Guide](https://developers-docs.imweb.me/guide)[Reference](https://developers-docs.imweb.me/reference)

Show sidebar

Search

*    OAuth2.0 Open Group  
*    Site-Info Open Group  
*    Member-Info Open Group  
*    Community Close Group  
    *        입력폼 목록 조회 HTTP Method: GET
    *        입력폼 상세 조회 HTTP Method: GET
    *        입력폼 제출 목록 조회 HTTP Method: GET
    *        입력폼 제출 상세 조회 HTTP Method: GET
    *        Q&A 목록 조회 HTTP Method: GET
    *        Q&A 답변 등록 HTTP Method: POST
    *        Q&A 답글 목록 조회 HTTP Method: GET
    *        Q&A 조회 HTTP Method: GET
    *        구매평 작성 HTTP Method: POST
    *       구매평 목록 조회 HTTP Method: GET 
    *        구매평 수정 HTTP Method: PUT
    *        구매평 삭제 HTTP Method: DEL
    *        구매평 조회 HTTP Method: GET
    *        구매평 답글 등록 HTTP Method: POST
    *        구매평 답글 목록 조회 HTTP Method: GET
    *        구매평 답글 삭제 HTTP Method: DEL
    *       구매평 목록 조회 (커서 기반) HTTP Method: GET 

*    Promotion Open Group  
*    Product Open Group  
*    Order Open Group  
*    Script Open Group  
*    Payment Open Group  

GET

Server: https://openapi.imweb.me

/community/forms

Copy URL Send Send get request to https://openapi.imweb.me/community/forms

GET

Copy URL Send Send get request to https://openapi.imweb.me/community/forms

Close Client

입력폼 목록 조회

All Auth Cookies Headers Query

All

## Authentication Required

Selected Auth Type: access-token

OAuth2.0 Access Token
Bearer Token  : 

Show Password

## Variables

| Enabled | Key | Value |
| --- | --- | --- |

## Cookies

| Enabled | Key | Value |
| --- | --- | --- |
| - [x] |  |  |

## Headers

| Enabled | Key | Value |
| --- | --- | --- |
| - [x] | accept | application/json |
| - [x] |  |  |

## Query Parameters

 Clear All Query Parameters

| Enabled | Key | Value |
| --- | --- | --- |
| - [x] | page Required | 1 |
| - [x] | limit Required | 10 |
| - [x] | unitCode Required | u20250402e3b6987310679 |
| - [x] | formCreateTimeType | GTE |
| - [x] | formCreateTime | 2021-01-01T00:00:00.000Z |
| - [x] | formEditTimeType | GTE |
| - [x] | formEditTime | 2021-01-01T00:00:00.000Z |
| - [x] |  |  |

## Request Body

None

No Body

## Code Snippet (Collapsed)

Shell Curl 

 Response 

All Cookies Headers Body

All

[Powered By Scalar.com](https://www.scalar.com/)

 .,,uod8B8bou,,. ..,uod8BBBBBBBBBBBBBBBBRPFT?l!i:. ||||||||||||||!?TFPRBBBBBBBBBBBBBBB8m=, |||| '""^^!!||||||||||TFPRBBBVT!:...! |||| '""^^!!|||||?!:.......! |||| ||||.........! |||| ||||.........! |||| ||||.........! |||| ||||.........! |||| ||||.........! |||| ||||.........! ||||, ||||.........` |||||!!-._ ||||.......;. ':!|||||||||!!-._ ||||.....bBBBBWdou,. bBBBBB86foi!|||||||!!-..:|||!..bBBBBBBBBBBBBBBY! ::!?TFPRBBBBBB86foi!||||||||!!bBBBBBBBBBBBBBBY..! :::::::::!?TFPRBBBBBB86ftiaabBBBBBBBBBBBBBBY....! :::;`"^!:;::::::!?TFPRBBBBBBBBBBBBBBBBBBBY......! ;::::::...''^::::::::::!?TFPRBBBBBBBBBBY........! .ob86foi;::::::::::::::::::::::::!?TFPRBY..........` .b888888888886foi;:::::::::::::::::::::::..........` .b888888888888888888886foi;::::::::::::::::...........b888888888888888888888888888886foi;:::::::::......`!Tf998888888888888888888888888888888886foi;:::....` '"^!|Tf9988888888888888888888888888888888!::..` '"^!|Tf998888888888888888888888889!! '` '"^!|Tf9988888888888888888!!` iBBbo. '"^!|Tf998888888889!` WBBBBbo. '"^!|Tf9989!` YBBBP^' '"^!` `

 Send Request 

ctrl Control

↵Enter
