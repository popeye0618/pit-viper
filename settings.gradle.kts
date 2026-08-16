// Gradle 이 빌드를 시작할 때 가장 먼저 읽는 파일. 프로젝트 이름을 정한다.
//
// 이 저장소는 "스킬이 설치된 스프링 프로젝트" 하나다.
// 루트가 곧 스프링 프로젝트이고, 스킬은 .claude/skills/pit-viper/ 에 함께 산다.
// clone 한 사람이 곧바로 ./gradlew test 를 돌려볼 수 있는 형태가 데모로서 제일 읽기 쉽다.

rootProject.name = "pit-viper"
